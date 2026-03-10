"""Endpoints de gerenciamento de Produtos (Org -> Produto)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_data_session, require_role
from app.models.user import User

router = APIRouter()


# --- Schemas ---

class ProductCreate(BaseModel):
    name: str
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class MemberAdd(BaseModel):
    user_id: str


# --- Helpers ---

def _require_admin(user: User = Depends(require_role("admin"))) -> User:
    return user


def _get_product_or_404(db: Session, product_id: str, org_id: str) -> dict:
    row = db.execute(text("""
        SELECT * FROM products WHERE id = :id AND org_id = :org_id
    """), {"id": product_id, "org_id": org_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return dict(row)


# --- CRUD Produtos ---

@router.post("/products", status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_data_session),
    user: User = Depends(_require_admin),
):
    product_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO products (id, org_id, name, description, is_active)
        VALUES (:id, :org_id, :name, :description, true)
    """), {
        "id": product_id,
        "org_id": user.org_id,
        "name": body.name,
        "description": body.description,
    })
    db.commit()

    return {
        "id": product_id,
        "org_id": user.org_id,
        "name": body.name,
        "description": body.description,
        "is_active": True,
    }


@router.get("/products")
def list_products(
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
):
    """Lista produtos do usuario atual.
    Admin ve todos da org. Dev/suporte ve apenas os que e membro.
    """
    if user.role == "admin":
        rows = db.execute(text("""
            SELECT p.*,
                (SELECT COUNT(*) FROM product_memberships pm WHERE pm.product_id = p.id) as member_count
            FROM products p
            WHERE p.org_id = :org_id AND p.is_active = true
            ORDER BY p.created_at
        """), {"org_id": user.org_id}).mappings().all()
    else:
        rows = db.execute(text("""
            SELECT p.*,
                (SELECT COUNT(*) FROM product_memberships pm WHERE pm.product_id = p.id) as member_count
            FROM products p
            INNER JOIN product_memberships pm ON pm.product_id = p.id AND pm.user_id = :user_id
            WHERE p.org_id = :org_id AND p.is_active = true
            ORDER BY p.created_at
        """), {"org_id": user.org_id, "user_id": user.id}).mappings().all()

    return [
        {
            "id": r["id"],
            "org_id": r["org_id"],
            "name": r["name"],
            "description": r["description"],
            "is_active": r["is_active"],
            "member_count": r["member_count"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        }
        for r in rows
    ]


@router.get("/products/{product_id}")
def get_product(
    product_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
):
    product = _get_product_or_404(db, product_id, user.org_id)

    # Verifica acesso para não-admin
    if user.role != "admin":
        membership = db.execute(text("""
            SELECT 1 FROM product_memberships
            WHERE product_id = :product_id AND user_id = :user_id
        """), {"product_id": product_id, "user_id": user.id}).first()

        if not membership:
            raise HTTPException(status_code=403, detail="Voce nao e membro deste produto")

    return product


@router.put("/products/{product_id}")
def update_product(
    product_id: str,
    body: ProductUpdate,
    db: Session = Depends(get_data_session),
    user: User = Depends(_require_admin),
):
    _get_product_or_404(db, product_id, user.org_id)

    updates = []
    params: dict = {"id": product_id, "org_id": user.org_id}

    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.description is not None:
        updates.append("description = :description")
        params["description"] = body.description

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    updates.append("updated_at = now()")
    db.execute(text(f"""
        UPDATE products SET {', '.join(updates)}
        WHERE id = :id AND org_id = :org_id
    """), params)
    db.commit()

    return _get_product_or_404(db, product_id, user.org_id)


@router.delete("/products/{product_id}")
def archive_product(
    product_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(_require_admin),
):
    _get_product_or_404(db, product_id, user.org_id)

    db.execute(text("""
        UPDATE products SET is_active = false, updated_at = now()
        WHERE id = :id AND org_id = :org_id
    """), {"id": product_id, "org_id": user.org_id})
    db.commit()

    return {"detail": "Produto arquivado"}


# --- Membros ---

@router.post("/products/{product_id}/members", status_code=201)
def add_member(
    product_id: str,
    body: MemberAdd,
    db: Session = Depends(get_data_session),
    user: User = Depends(_require_admin),
):
    _get_product_or_404(db, product_id, user.org_id)

    # Verifica se o user pertence à mesma org
    target_user = db.execute(text("""
        SELECT id, name, email, role FROM users
        WHERE id = :user_id AND org_id = :org_id AND is_active = true
    """), {"user_id": body.user_id, "org_id": user.org_id}).mappings().first()

    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado na organizacao")

    # Verifica duplicata
    existing = db.execute(text("""
        SELECT 1 FROM product_memberships
        WHERE product_id = :product_id AND user_id = :user_id
    """), {"product_id": product_id, "user_id": body.user_id}).first()

    if existing:
        raise HTTPException(status_code=409, detail="Usuario ja e membro deste produto")

    membership_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO product_memberships (id, product_id, user_id)
        VALUES (:id, :product_id, :user_id)
    """), {"id": membership_id, "product_id": product_id, "user_id": body.user_id})
    db.commit()

    return {
        "id": membership_id,
        "product_id": product_id,
        "user_id": body.user_id,
        "user_name": target_user["name"],
        "user_email": target_user["email"],
    }


@router.delete("/products/{product_id}/members/{member_user_id}")
def remove_member(
    product_id: str,
    member_user_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(_require_admin),
):
    _get_product_or_404(db, product_id, user.org_id)

    result = db.execute(text("""
        DELETE FROM product_memberships
        WHERE product_id = :product_id AND user_id = :user_id
    """), {"product_id": product_id, "user_id": member_user_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Membro nao encontrado")

    return {"detail": "Membro removido"}


@router.get("/products/{product_id}/members")
def list_members(
    product_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(_require_admin),
):
    _get_product_or_404(db, product_id, user.org_id)

    rows = db.execute(text("""
        SELECT u.id, u.name, u.email, u.role, u.avatar_url, pm.created_at as joined_at
        FROM product_memberships pm
        INNER JOIN users u ON u.id = pm.user_id
        WHERE pm.product_id = :product_id
        ORDER BY pm.created_at
    """), {"product_id": product_id}).mappings().all()

    return [
        {
            "user_id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "role": r["role"],
            "avatar_url": r["avatar_url"],
            "joined_at": str(r["joined_at"]) if r["joined_at"] else None,
        }
        for r in rows
    ]
