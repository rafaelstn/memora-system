from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth import decode_supabase_jwt
from app.db.session import get_db
from app.models.organization import Organization
from app.models.product import Product, ProductMembership
from app.models.user import User

security = HTTPBearer()

# Cache de org mode para evitar queries repetitivas no Supabase
_org_mode_cache: dict[str, str] = {}


def get_session(db: Session = Depends(get_db)) -> Session:
    """Retorna session do Supabase (banco central).

    Usar para: auth, users, invites, llm_providers, organizations,
    enterprise_db_configs, notification_preferences, alert_webhooks.
    """
    return db


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    payload = decode_supabase_jwt(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    user.last_activity = datetime.utcnow()
    db.commit()
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso restrito a: {', '.join(roles)}",
            )
        return user
    return checker


def get_data_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Session:
    """Retorna session do banco correto para dados operacionais.

    - SaaS: retorna session do Supabase (mesma de sempre)
    - Enterprise: retorna session do banco externo do cliente

    Usar para: products, code_chunks, conversations, messages,
    monitored_projects, log_entries, error_alerts, incidents,
    knowledge_*, code_reviews, security_*, dast_*, business_rules,
    impact_*, code_generations, executive_snapshots, repo_docs, etc.
    """
    org_id = user.org_id

    # Verificar modo da org (com cache em memoria)
    if org_id not in _org_mode_cache:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        _org_mode_cache[org_id] = org.mode if org else "saas"

    if _org_mode_cache[org_id] == "enterprise":
        from app.core.enterprise_db import get_enterprise_session
        try:
            return get_enterprise_session(org_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível conectar ao banco de dados da sua organização. "
                       "Verifique as configurações em /setup/enterprise.",
            )

    return db


def invalidate_org_mode_cache(org_id: str):
    """Remove org do cache de modo. Chamar quando org.mode ou enterprise_db_configs mudar."""
    _org_mode_cache.pop(org_id, None)


def get_current_product(
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    x_product_id: Optional[str] = Header(None, alias="X-Product-ID"),
    product_id: Optional[str] = Query(None),
) -> Product:
    """Resolve e valida o produto atual a partir do header X-Product-ID ou query param product_id.

    - Admin da org: acesso a qualquer produto da org
    - Dev/suporte: precisa ser membro via product_memberships

    Nota: usa get_data_session pois products e product_memberships sao tabelas operacionais.
    """
    pid = x_product_id or product_id
    if not pid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product ID obrigatório (header X-Product-ID ou query param product_id)",
        )

    product = db.query(Product).filter(
        Product.id == pid,
        Product.org_id == user.org_id,
        Product.is_active.is_(True),
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado ou não pertence à sua organização",
        )

    # Admin tem acesso total a todos os produtos da org
    if user.role == "admin":
        return product

    # Dev/suporte precisa ser membro
    membership = db.query(ProductMembership).filter(
        ProductMembership.product_id == pid,
        ProductMembership.user_id == user.id,
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não é membro deste produto",
        )

    return product


# ── Plan dependencies ───────────────────────────────────────


def get_current_plan(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """Retorna o status do plano da org do usuario.

    Returns dict with keys: plan, status, days_remaining, trial_ends_at, is_active
    """
    row = db.execute(
        text("SELECT * FROM org_plans WHERE org_id = :org_id ORDER BY created_at DESC LIMIT 1"),
        {"org_id": user.org_id},
    ).mappings().first()

    if not row:
        # Org sem plano (legado) — tratar como trial expirado
        return {
            "plan": "pro_trial",
            "status": "trial_expired",
            "days_remaining": 0,
            "trial_ends_at": None,
            "is_active": False,
        }

    plan = row["plan"]
    is_active = row["is_active"]
    now = datetime.utcnow()

    if not is_active:
        return {
            "plan": plan,
            "status": "inactive",
            "days_remaining": 0,
            "trial_ends_at": row.get("trial_ends_at"),
            "is_active": False,
        }

    if plan == "pro_trial":
        trial_ends = row.get("trial_ends_at")
        if trial_ends and now > trial_ends:
            return {
                "plan": plan,
                "status": "trial_expired",
                "days_remaining": 0,
                "trial_ends_at": trial_ends,
                "trial_started_at": row.get("trial_started_at"),
                "is_active": True,
            }
        days_left = max(0, (trial_ends - now).days) if trial_ends else 0
        return {
            "plan": plan,
            "status": "trial_active",
            "days_remaining": days_left,
            "trial_ends_at": trial_ends,
            "trial_started_at": row.get("trial_started_at"),
            "is_active": True,
        }

    # pro, enterprise, customer — active
    return {
        "plan": plan,
        "status": "active",
        "days_remaining": None,
        "trial_ends_at": None,
        "is_active": True,
    }


def require_active_plan(
    plan_info: dict = Depends(get_current_plan),
    user: User = Depends(get_current_user),
) -> dict:
    """Bloqueia acesso se o plano estiver expirado ou inativo. Retorna 402."""
    if plan_info["status"] in ("trial_expired", "inactive"):
        days_used = 7  # trial completo
        if plan_info.get("trial_started_at"):
            delta = datetime.utcnow() - plan_info["trial_started_at"]
            days_used = min(delta.days, 7)
        raise HTTPException(
            status_code=402,
            detail={
                "error": "plan_expired",
                "message": "Seu trial de 7 dias expirou.",
                "days_used": days_used,
                "upgrade_url": "/upgrade",
            },
        )
    return plan_info
