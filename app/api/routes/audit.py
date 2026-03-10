"""Rotas do audit log — consulta de logs de auditoria (admin only)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.core.audit import get_audit_log
from app.models.user import User

router = APIRouter(prefix="/admin/audit")


@router.get("")
def list_audit_log(
    action: str | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Lista audit log da organização (admin only)."""
    entries = get_audit_log(
        db,
        user.org_id,
        action=action,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return entries
