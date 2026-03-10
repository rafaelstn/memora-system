"""Audit log service — registra ações sensíveis no sistema."""
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    *,
    user_id: str | None,
    org_id: str,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Registra ação no audit log. Nunca falha — erros são apenas logados."""
    try:
        db.execute(
            text("""
                INSERT INTO audit_log (org_id, user_id, action, resource_type, resource_id, detail, ip_address)
                VALUES (:org_id, :uid, :action, :rtype, :rid, :detail, :ip)
            """),
            {
                "org_id": org_id,
                "uid": user_id,
                "action": action,
                "rtype": resource_type,
                "rid": resource_id,
                "detail": detail,
                "ip": ip_address,
            },
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Falha ao gravar audit log: {e}")
        try:
            db.rollback()
        except Exception:
            pass


def get_audit_log(
    db: Session,
    org_id: str,
    *,
    action: str | None = None,
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Retorna entradas do audit log com filtros opcionais."""
    conditions = ["org_id = :org_id"]
    params: dict = {"org_id": org_id, "lim": limit, "off": offset}

    if action:
        conditions.append("action = :action")
        params["action"] = action
    if user_id:
        conditions.append("user_id = :user_id")
        params["user_id"] = user_id

    where = " AND ".join(conditions)
    rows = db.execute(
        text(f"""
            SELECT id, org_id, user_id, action, resource_type, resource_id,
                   detail, ip_address, created_at
            FROM audit_log
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
        """),
        params,
    ).mappings().all()

    return [dict(r) for r in rows]
