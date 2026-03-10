"""Endpoints de geracao de codigo com contexto real."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session, require_role
from app.core.code_generator import CodeGenerator
from app.models.product import Product
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


class CodeGenRequest(BaseModel):
    description: str
    type: str = "function"
    repo_name: str
    file_path: str | None = None
    use_context: bool = True


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/codegen/generate")
def generate_code(
    req: CodeGenRequest,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Gera codigo com contexto real via SSE streaming."""
    gen_id = str(uuid.uuid4())

    def stream():
        generator = CodeGenerator(db, user.org_id)
        full_content = ""
        context_used = {}

        try:
            for event in generator.generate_stream(
                description=req.description,
                request_type=req.type,
                repo_name=req.repo_name,
                file_path=req.file_path,
                use_context=req.use_context,
            ):
                if event["type"] == "context":
                    yield _sse_event({"type": "context", "gen_id": gen_id, **event["data"]})
                elif event["type"] == "token":
                    yield _sse_event({"type": "token", "content": event["data"]})
                elif event["type"] == "error":
                    yield _sse_event({"type": "error", "message": event["data"]})
                elif event["type"] == "done":
                    full_content = event["data"]["full_content"]
                    context_used = event["data"]["context_used"]

            # Separa codigo da explicacao
            code, explanation = _split_code_explanation(full_content)

            # Salva no banco
            try:
                db.execute(text("""
                    INSERT INTO code_generations
                        (id, org_id, product_id, repo_name, user_id, request_description, request_type,
                         file_path, use_context, context_used, generated_code, explanation)
                    VALUES (:id, :org_id, :product_id, :repo_name, :user_id, :desc, :type,
                            :file_path, :use_context, :context, :code, :explanation)
                """), {
                    "id": gen_id,
                    "org_id": user.org_id,
                    "product_id": product.id,
                    "repo_name": req.repo_name,
                    "user_id": user.id,
                    "desc": req.description,
                    "type": req.type,
                    "file_path": req.file_path,
                    "use_context": req.use_context,
                    "context": json.dumps(context_used),
                    "code": code,
                    "explanation": explanation,
                })
                db.commit()
            except Exception as e:
                logger.error(f"Erro ao salvar geracao: {e}")

            yield _sse_event({"type": "done", "gen_id": gen_id})

        except Exception as e:
            logger.error(f"Erro no streaming de codegen: {e}")
            yield _sse_event({"type": "error", "message": str(e)})

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/codegen/history")
def codegen_history(
    page: int = Query(1, ge=1),
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Lista historico de geracoes do usuario."""
    offset = (page - 1) * 20

    rows = db.execute(text("""
        SELECT id, repo_name, request_description, request_type, created_at
        FROM code_generations
        WHERE user_id = :user_id AND product_id = :product_id
        ORDER BY created_at DESC
        LIMIT 20 OFFSET :offset
    """), {"user_id": user.id, "product_id": product.id, "offset": offset}).mappings().all()

    total_row = db.execute(text("""
        SELECT COUNT(*) as total FROM code_generations
        WHERE user_id = :user_id AND product_id = :product_id
    """), {"user_id": user.id, "product_id": product.id}).mappings().first()

    return {
        "generations": [
            {
                "id": r["id"],
                "repo_name": r["repo_name"],
                "title": r["request_description"][:80],
                "request_type": r["request_type"],
                "created_at": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in rows
        ],
        "total": total_row["total"] if total_row else 0,
        "page": page,
    }


@router.get("/codegen/{gen_id}")
def get_generation(
    gen_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Retorna detalhes de uma geracao."""
    row = db.execute(text("""
        SELECT id, repo_name, request_description, request_type, file_path,
               use_context, context_used, generated_code, explanation,
               model_used, tokens_used, cost_usd, created_at
        FROM code_generations
        WHERE id = :id AND product_id = :product_id
    """), {"id": gen_id, "product_id": product.id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Geracao nao encontrada")

    return {
        "id": row["id"],
        "repo_name": row["repo_name"],
        "request_description": row["request_description"],
        "request_type": row["request_type"],
        "file_path": row["file_path"],
        "use_context": row["use_context"],
        "context_used": row["context_used"],
        "generated_code": row["generated_code"],
        "explanation": row["explanation"],
        "model_used": row["model_used"],
        "tokens_used": row["tokens_used"],
        "cost_usd": row["cost_usd"],
        "created_at": str(row["created_at"]) if row["created_at"] else None,
    }


def _split_code_explanation(content: str) -> tuple[str, str]:
    """Tenta separar o codigo gerado da explicacao."""
    # Procura por marcadores comuns
    markers = [
        "Por que o codigo foi gerado assim:",
        "Explicacao:",
        "Decisoes tomadas:",
        "## Explicacao",
        "### Explicacao",
    ]

    for marker in markers:
        if marker in content:
            idx = content.index(marker)
            return content[:idx].strip(), content[idx:].strip()

    # Se nao encontrou marcador, retorna tudo como codigo
    return content.strip(), ""
