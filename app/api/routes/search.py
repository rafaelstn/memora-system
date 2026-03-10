"""Rota de busca global — atravessa todos os modulos do Memora."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/search")


@router.get("/global")
def search_global(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Busca global em todos os modulos do Memora."""
    if not q or not q.strip():
        raise HTTPException(400, "Query vazia")

    from app.core.global_search import global_search

    return global_search(
        db=db,
        query=q.strip(),
        org_id=user.org_id,
        product_id=product.id,
        user_role=user.role,
        limit=limit,
    )
