"""Rotas de gestao de planos e trial."""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_plan, get_current_user, get_session, require_role
from app.config import settings
from app.models.user import User

router = APIRouter(prefix="/admin/plan")


# ── Schemas ──────────────────────────────────────────


class ContactRequest(BaseModel):
    contact_reason: str  # 'upgrade_pro' | 'enterprise' | 'customer'
    message: str = ""


class UpdatePlanRequest(BaseModel):
    plan: str  # 'pro_trial' | 'pro' | 'enterprise' | 'customer'
    is_active: bool = True
    notes: str = ""


class ExtendTrialRequest(BaseModel):
    days: int = 7


# ── Org admin routes ────────────────────────────────


@router.get("")
def get_plan_status(
    plan_info: dict = Depends(get_current_plan),
    user: User = Depends(require_role("admin")),
):
    """Retorna status atual do plano da organizacao."""
    # Serialize datetimes
    result = {**plan_info}
    for key in ("trial_ends_at", "trial_started_at"):
        if key in result and result[key] is not None:
            result[key] = result[key].isoformat() if hasattr(result[key], "isoformat") else str(result[key])
    return result


@router.post("/contact")
def submit_contact(
    body: ContactRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Registra intencao de upgrade e envia email para o admin master."""
    valid_reasons = ("upgrade_pro", "enterprise", "customer")
    if body.contact_reason not in valid_reasons:
        raise HTTPException(400, f"Motivo invalido. Use: {', '.join(valid_reasons)}")

    contact_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO plan_contacts (id, org_id, user_id, user_name, user_email, contact_reason, message)
            VALUES (:id, :org_id, :user_id, :name, :email, :reason, :message)
        """),
        {
            "id": contact_id,
            "org_id": user.org_id,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "reason": body.contact_reason,
            "message": body.message,
        },
    )
    db.commit()

    # Enviar email para o admin master
    _send_contact_email(user, body.contact_reason, body.message)

    return {"id": contact_id, "status": "sent", "message": "Recebemos seu contato. Rafael entrara em contato em ate 24h."}


def _send_contact_email(user: User, reason: str, message: str):
    """Envia email de contato para o admin master."""
    if not settings.master_admin_email:
        return

    try:
        from app.core.email_client import send

        reason_labels = {
            "upgrade_pro": "Upgrade para PRO",
            "enterprise": "Plano Enterprise",
            "customer": "Plano Customer",
        }
        subject = f"[Memora] Contato de plano: {reason_labels.get(reason, reason)}"
        body_html = f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h2 style="color: #4f46e5;">Novo contato de plano</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 8px; font-weight: bold;">Nome:</td><td style="padding: 8px;">{user.name}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Email:</td><td style="padding: 8px;">{user.email}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Org ID:</td><td style="padding: 8px;">{user.org_id}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Motivo:</td><td style="padding: 8px;">{reason_labels.get(reason, reason)}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Mensagem:</td><td style="padding: 8px;">{message or '(sem mensagem)'}</td></tr>
            </table>
        </div>
        """
        send(settings.master_admin_email, subject, body_html)
    except Exception:
        pass  # Nao bloquear o contato se o email falhar


# ── Master admin routes ─────────────────────────────


def _require_master_admin(user: User = Depends(get_current_user)) -> User:
    """Verifica se o usuario e o admin master (MASTER_ADMIN_EMAIL)."""
    if not settings.master_admin_email:
        raise HTTPException(403, "MASTER_ADMIN_EMAIL nao configurado")
    if user.email != settings.master_admin_email:
        raise HTTPException(403, "Acesso restrito ao administrador master")
    return user


@router.get("/all")
def list_all_plans(
    db: Session = Depends(get_session),
    user: User = Depends(_require_master_admin),
):
    """Lista todas as orgs com seus planos (master admin only)."""
    rows = db.execute(
        text("""
            SELECT o.id as org_id, o.name as org_name, o.mode,
                   p.id as plan_id, p.plan, p.trial_started_at, p.trial_ends_at,
                   p.is_active, p.activated_by, p.notes, p.created_at, p.updated_at
            FROM organizations o
            LEFT JOIN org_plans p ON p.org_id = o.id
            ORDER BY o.created_at DESC
        """)
    ).mappings().all()

    return [dict(r) for r in rows]


@router.get("/contacts")
def list_contacts(
    unread_only: bool = False,
    db: Session = Depends(get_session),
    user: User = Depends(_require_master_admin),
):
    """Lista contatos de plano recebidos (master admin only)."""
    query = "SELECT * FROM plan_contacts"
    params = {}
    if unread_only:
        query += " WHERE is_read = false"
    query += " ORDER BY created_at DESC LIMIT 50"

    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]


@router.post("/contacts/{contact_id}/read")
def mark_contact_read(
    contact_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(_require_master_admin),
):
    """Marca contato como lido (master admin only)."""
    db.execute(
        text("UPDATE plan_contacts SET is_read = true WHERE id = :id"),
        {"id": contact_id},
    )
    db.commit()
    return {"status": "ok"}


@router.put("/{org_id}")
def update_org_plan(
    org_id: str,
    body: UpdatePlanRequest,
    db: Session = Depends(get_session),
    user: User = Depends(_require_master_admin),
):
    """Atualiza plano de uma org (master admin only)."""
    valid_plans = ("pro_trial", "pro", "enterprise", "customer")
    if body.plan not in valid_plans:
        raise HTTPException(400, f"Plano invalido. Use: {', '.join(valid_plans)}")

    # Check org exists
    org = db.execute(
        text("SELECT id FROM organizations WHERE id = :oid"),
        {"oid": org_id},
    ).mappings().first()
    if not org:
        raise HTTPException(404, "Organizacao nao encontrada")

    existing = db.execute(
        text("SELECT id FROM org_plans WHERE org_id = :oid"),
        {"oid": org_id},
    ).mappings().first()

    now = datetime.utcnow()

    if existing:
        db.execute(
            text("""
                UPDATE org_plans
                SET plan = :plan, is_active = :active, activated_by = :by,
                    notes = :notes, updated_at = :now
                WHERE org_id = :oid
            """),
            {
                "plan": body.plan,
                "active": body.is_active,
                "by": user.id,
                "notes": body.notes,
                "now": now,
                "oid": org_id,
            },
        )
    else:
        db.execute(
            text("""
                INSERT INTO org_plans (id, org_id, plan, is_active, activated_by, notes, created_at, updated_at)
                VALUES (:id, :oid, :plan, :active, :by, :notes, :now, :now)
            """),
            {
                "id": str(uuid.uuid4()),
                "oid": org_id,
                "plan": body.plan,
                "active": body.is_active,
                "by": user.id,
                "notes": body.notes,
                "now": now,
            },
        )

    db.commit()
    return {"status": "updated", "org_id": org_id, "plan": body.plan}


@router.post("/{org_id}/extend-trial")
def extend_trial(
    org_id: str,
    body: ExtendTrialRequest,
    db: Session = Depends(get_session),
    user: User = Depends(_require_master_admin),
):
    """Estende trial de uma org (master admin only)."""
    if body.days < 1 or body.days > 90:
        raise HTTPException(400, "Dias deve estar entre 1 e 90")

    row = db.execute(
        text("SELECT * FROM org_plans WHERE org_id = :oid"),
        {"oid": org_id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Plano nao encontrado para esta org")

    current_ends = row["trial_ends_at"] or datetime.utcnow()
    new_ends = current_ends + timedelta(days=body.days)

    db.execute(
        text("""
            UPDATE org_plans
            SET trial_ends_at = :ends, is_active = true, updated_at = :now
            WHERE org_id = :oid
        """),
        {"ends": new_ends, "now": datetime.utcnow(), "oid": org_id},
    )
    db.commit()

    return {"status": "extended", "org_id": org_id, "new_trial_ends_at": new_ends.isoformat()}


@router.post("/{org_id}/deactivate")
def deactivate_plan(
    org_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(_require_master_admin),
):
    """Desativa plano de uma org (master admin only)."""
    db.execute(
        text("UPDATE org_plans SET is_active = false, updated_at = :now WHERE org_id = :oid"),
        {"now": datetime.utcnow(), "oid": org_id},
    )
    db.commit()
    return {"status": "deactivated", "org_id": org_id}
