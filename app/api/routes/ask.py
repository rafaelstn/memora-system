from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session
from app.core.assistant import ask_assistant
from app.core.rate_limit import ASK_LIMIT, limiter
from app.models.product import Product
from app.models.user import User

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    repo_name: str
    max_chunks: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]


@router.post("/ask", response_model=AskResponse)
@limiter.limit(ASK_LIMIT)
def ask(
    request: Request,
    body: AskRequest,
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    result = ask_assistant(
        db=db,
        question=body.question,
        repo_name=body.repo_name,
        max_chunks=body.max_chunks,
        org_id=user.org_id,
        product_id=product.id,
    )
    return result
