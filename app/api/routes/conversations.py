import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session
from app.models.product import Product
from app.models.user import User

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


class ConversationCreate(BaseModel):
    repo_name: str
    user_id: str
    title: str


class MessageCreate(BaseModel):
    conversation_id: str
    role: str
    content: str
    sources: list[dict] | None = None
    model_used: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None


@router.get("/conversations")
def list_conversations(
    repo_name: str = Query(...),
    user_id: str | None = Query(None),
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    query = "SELECT * FROM conversations WHERE repo_name = :repo_name AND product_id = :product_id"
    params: dict = {"repo_name": repo_name, "product_id": product.id}
    if user_id:
        query += " AND user_id = :user_id"
        params["user_id"] = user_id
    query += " ORDER BY updated_at DESC"

    result = db.execute(text(query), params)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.post("/conversations")
def create_conversation(body: ConversationCreate, db: Session = Depends(get_data_session), user: User = Depends(get_current_user), product: Product = Depends(get_current_product)):
    conv_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO conversations (id, product_id, repo_name, user_id, title)
            VALUES (:id, :product_id, :repo_name, :user_id, :title)
        """),
        {"id": conv_id, "product_id": product.id, "repo_name": body.repo_name, "user_id": body.user_id, "title": body.title},
    )
    db.commit()
    return {"id": conv_id, "repo_name": body.repo_name, "title": body.title}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: str, db: Session = Depends(get_data_session), user: User = Depends(get_current_user), product: Product = Depends(get_current_product)):
    result = db.execute(
        text("DELETE FROM conversations WHERE id = :id AND product_id = :product_id"),
        {"id": conv_id, "product_id": product.id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return {"deleted": True}


@router.get("/conversations/{conv_id}/messages")
def list_messages(conv_id: str, db: Session = Depends(get_data_session), user: User = Depends(get_current_user), product: Product = Depends(get_current_product)):
    # Validate conversation belongs to product
    conv = db.execute(
        text("SELECT id FROM conversations WHERE id = :id AND product_id = :product_id"),
        {"id": conv_id, "product_id": product.id},
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    result = db.execute(
        text("SELECT * FROM messages WHERE conversation_id = :cid ORDER BY created_at ASC"),
        {"cid": conv_id},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.post("/messages")
def create_message(body: MessageCreate, db: Session = Depends(get_data_session), user: User = Depends(get_current_user), product: Product = Depends(get_current_product)):
    # Validate conversation belongs to product
    conv = db.execute(
        text("SELECT id FROM conversations WHERE id = :id AND product_id = :product_id"),
        {"id": body.conversation_id, "product_id": product.id},
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    msg_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO messages (id, conversation_id, role, content, sources, model_used, tokens_used, cost_usd)
            VALUES (:id, :cid, :role, :content, :sources::jsonb, :model, :tokens, :cost)
        """),
        {
            "id": msg_id,
            "cid": body.conversation_id,
            "role": body.role,
            "content": body.content,
            "sources": str(body.sources) if body.sources else None,
            "model": body.model_used,
            "tokens": body.tokens_used,
            "cost": body.cost_usd,
        },
    )
    db.execute(
        text("UPDATE conversations SET updated_at = now() WHERE id = :cid"),
        {"cid": body.conversation_id},
    )
    db.commit()
    return {"id": msg_id}
