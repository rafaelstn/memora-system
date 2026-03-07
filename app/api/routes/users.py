from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.models.user import User

router = APIRouter(
    prefix="/users",
    dependencies=[Depends(require_role("admin"))],
)


class AddByEmailRequest(BaseModel):
    email: str
    role: str


@router.get("/search")
def search_users(
    email: str = Query(..., min_length=2),
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Busca usuarios por email dentro da organizacao. Maximo 10 resultados."""
    users = (
        db.query(User)
        .filter(User.org_id == user.org_id, User.email.ilike(f"%{email}%"))
        .limit(10)
        .all()
    )
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/add-by-email")
def add_user_by_email(
    body: AddByEmailRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Adiciona usuario existente a um time com uma role."""
    if body.role not in ("dev", "suporte"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role deve ser 'dev' ou 'suporte'",
        )

    target = db.query(User).filter(User.email == body.email, User.org_id == user.org_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado na organização.",
        )

    if target.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já é administrador.",
        )

    target.role = body.role
    db.commit()

    return {
        "success": True,
        "user": {
            "name": target.name,
            "email": target.email,
            "role": target.role,
        },
    }
