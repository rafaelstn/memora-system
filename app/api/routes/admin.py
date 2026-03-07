import logging
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.config import settings
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_role("admin"))])
logger = logging.getLogger(__name__)


def _get_admin_user(user: User = Depends(require_role("admin"))) -> User:
    return user


# --- Metrics ---
@router.get("/admin/metrics")
def get_metrics(db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    org_id = user.org_id
    row = db.execute(text("""
        SELECT
            COUNT(*) as total_questions,
            COALESCE(SUM(m.cost_usd), 0) as total_cost_usd,
            COALESCE(AVG(m.cost_usd), 0) as avg_cost_usd
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE m.role = 'assistant' AND c.org_id = :org_id
    """), {"org_id": org_id}).mappings().first()

    active_users = db.execute(text("""
        SELECT COUNT(DISTINCT user_id) as cnt
        FROM conversations
        WHERE updated_at >= now() - interval '7 days' AND org_id = :org_id
    """), {"org_id": org_id}).mappings().first()

    usd_to_brl = settings.usd_to_brl
    return {
        "total_questions": row["total_questions"],
        "total_cost_brl": round(float(row["total_cost_usd"]) * usd_to_brl, 2),
        "avg_cost_per_question_brl": round(float(row["avg_cost_usd"]) * usd_to_brl, 4),
        "active_users_7d": active_users["cnt"],
    }


@router.get("/admin/metrics/daily")
def get_daily_usage(days: int = Query(30), db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    org_id = user.org_id
    rows = db.execute(text("""
        SELECT
            DATE(m.created_at) as date,
            COUNT(*) as questions,
            COALESCE(SUM(m.cost_usd), 0) as cost_usd
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE m.role = 'assistant' AND m.created_at >= now() - :days * interval '1 day'
            AND c.org_id = :org_id
        GROUP BY DATE(m.created_at)
        ORDER BY date
    """), {"days": days, "org_id": org_id}).mappings().all()

    usd_to_brl = settings.usd_to_brl
    return [
        {
            "date": str(r["date"]),
            "questions": r["questions"],
            "cost_brl": round(float(r["cost_usd"]) * usd_to_brl, 2),
        }
        for r in rows
    ]


@router.get("/admin/metrics/users")
def get_user_usage(db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    org_id = user.org_id
    rows = db.execute(text("""
        SELECT
            u.id as user_id,
            u.name,
            u.role,
            COUNT(m.id) as total_questions,
            COALESCE(SUM(m.cost_usd), 0) as total_cost_usd,
            MAX(c.updated_at) as last_activity
        FROM users u
        LEFT JOIN conversations c ON c.user_id = u.id AND c.org_id = :org_id
        LEFT JOIN messages m ON m.conversation_id = c.id AND m.role = 'assistant'
        WHERE u.is_active = true AND u.org_id = :org_id
        GROUP BY u.id, u.name, u.role
        ORDER BY total_questions DESC
    """), {"org_id": org_id}).mappings().all()

    usd_to_brl = settings.usd_to_brl
    return [
        {
            "user_id": r["user_id"],
            "name": r["name"],
            "role": r["role"],
            "total_questions": r["total_questions"],
            "total_cost_brl": round(float(r["total_cost_usd"]) * usd_to_brl, 2),
            "last_activity": str(r["last_activity"]) if r["last_activity"] else None,
        }
        for r in rows
    ]


@router.get("/admin/metrics/models")
def get_model_usage(db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    org_id = user.org_id
    rows = db.execute(text("""
        SELECT
            COALESCE(m.model_used, 'unknown') as model,
            COUNT(*) as questions,
            COALESCE(SUM(m.cost_usd), 0) as cost_usd
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE m.role = 'assistant' AND m.model_used IS NOT NULL
            AND c.org_id = :org_id
        GROUP BY m.model_used
        ORDER BY questions DESC
    """), {"org_id": org_id}).mappings().all()

    total = sum(r["questions"] for r in rows) or 1
    return [
        {
            "model": r["model"],
            "questions": r["questions"],
            "cost_usd": round(float(r["cost_usd"]), 4),
            "percentage": round(r["questions"] / total * 100, 1),
        }
        for r in rows
    ]


# --- Users ---
@router.get("/admin/users")
def list_users(
    role: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_session),
    user: User = Depends(_get_admin_user),
):
    org_id = user.org_id
    query = "SELECT * FROM users WHERE org_id = :org_id"
    params: dict = {"org_id": org_id}

    if role:
        query += " AND role = :role"
        params["role"] = role
    if search:
        query += " AND (name ILIKE :search OR email ILIKE :search)"
        params["search"] = f"%{search}%"

    query += " ORDER BY created_at DESC"
    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]


class UserRoleUpdate(BaseModel):
    role: str


@router.patch("/admin/users/{user_id}/role")
def update_user_role(user_id: str, body: UserRoleUpdate, db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    if body.role not in ("admin", "dev", "suporte"):
        raise HTTPException(status_code=400, detail="Role inválida")
    result = db.execute(
        text("UPDATE users SET role = :role WHERE id = :id AND org_id = :org_id"),
        {"role": body.role, "id": user_id, "org_id": user.org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado na organização")
    return {"updated": True}


@router.patch("/admin/users/{user_id}/deactivate")
def toggle_user_active(user_id: str, db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    result = db.execute(
        text("UPDATE users SET is_active = NOT is_active WHERE id = :id AND org_id = :org_id"),
        {"id": user_id, "org_id": user.org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado na organização")
    return {"toggled": True}


# --- Invites ---
class InviteCreate(BaseModel):
    role: str
    email: str | None = None


@router.get("/admin/invites")
def list_invites(db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    rows = db.execute(
        text("SELECT * FROM invites WHERE org_id = :org_id ORDER BY created_at DESC"),
        {"org_id": user.org_id},
    ).mappings().all()
    return [dict(r) for r in rows]


@router.post("/admin/invites")
def create_invite(body: InviteCreate, db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    if body.role not in ("admin", "dev", "suporte"):
        raise HTTPException(status_code=400, detail="Role inválida")

    invite_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    db.execute(
        text("""
            INSERT INTO invites (id, org_id, token, role, email, created_by, status, expires_at)
            VALUES (:id, :org_id, :token, :role, :email, :created_by, 'pending', :expires_at)
        """),
        {
            "id": invite_id,
            "org_id": user.org_id,
            "token": token,
            "role": body.role,
            "email": body.email,
            "created_by": user.id,
            "expires_at": expires_at,
        },
    )
    db.commit()

    return {
        "id": invite_id,
        "token": token,
        "role": body.role,
        "invite_url": f"/invite/{token}",
        "expires_at": expires_at.isoformat(),
    }


@router.delete("/admin/invites/{invite_id}")
def revoke_invite(invite_id: str, db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    result = db.execute(
        text("DELETE FROM invites WHERE id = :id AND org_id = :org_id AND status = 'pending'"),
        {"id": invite_id, "org_id": user.org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Convite não encontrado ou já utilizado")
    return {"revoked": True}


# --- Repos info ---
@router.get("/admin/repos")
def list_repos(db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    rows = db.execute(text("""
        SELECT
            repo_name as name,
            COUNT(*) as chunks_count,
            MAX(created_at) as last_indexed
        FROM code_chunks
        WHERE org_id = :org_id
        GROUP BY repo_name
        ORDER BY repo_name
    """), {"org_id": user.org_id}).mappings().all()
    return [
        {
            "name": r["name"],
            "chunks_count": r["chunks_count"],
            "last_indexed": str(r["last_indexed"]) if r["last_indexed"] else None,
            "status": "indexed",
        }
        for r in rows
    ]


@router.delete("/admin/repos/{repo_name}")
def delete_repo(repo_name: str, db: Session = Depends(get_session), user: User = Depends(_get_admin_user)):
    """Delete a repository: removes all chunks, conversations, and messages."""
    org_id = user.org_id

    # Check repo exists
    count = db.execute(
        text("SELECT COUNT(*) FROM code_chunks WHERE repo_name = :repo AND org_id = :org_id"),
        {"repo": repo_name, "org_id": org_id},
    ).scalar()
    if count == 0:
        raise HTTPException(status_code=404, detail="Repositorio nao encontrado")

    # Delete messages from conversations of this repo
    db.execute(
        text("""
            DELETE FROM messages
            WHERE conversation_id IN (
                SELECT id FROM conversations WHERE repo_name = :repo AND org_id = :org_id
            )
        """),
        {"repo": repo_name, "org_id": org_id},
    )

    # Delete conversations
    db.execute(
        text("DELETE FROM conversations WHERE repo_name = :repo AND org_id = :org_id"),
        {"repo": repo_name, "org_id": org_id},
    )

    # Delete chunks
    result = db.execute(
        text("DELETE FROM code_chunks WHERE repo_name = :repo AND org_id = :org_id"),
        {"repo": repo_name, "org_id": org_id},
    )
    db.commit()

    logger.info("Repositorio '%s' deletado: %d chunks removidos (org=%s, user=%s)", repo_name, result.rowcount, org_id, user.id)
    return {"deleted": True, "repo_name": repo_name, "chunks_removed": result.rowcount}
