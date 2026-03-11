import json
import logging
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session
from app.config import settings
from app.core.assistant import SYSTEM_PROMPT, Assistant
from app.integrations import llm_router
from app.core.rate_limit import ASK_LIMIT, limiter
from app.integrations.llm_client import stream_llm
from app.models.product import Product
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)



class StreamAskRequest(BaseModel):
    question: str
    repo_name: str
    max_chunks: int = 5
    provider_id: str | None = None
    conversation_id: str | None = None


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_or_create_conversation(db: Session, user: User, repo_name: str, title: str, conversation_id: str | None = None, product_id: str | None = None) -> str:
    """Use given conversation_id, or get existing for this user+repo, or create a new one."""
    if conversation_id:
        row = db.execute(
            text("SELECT id FROM conversations WHERE id = :id AND product_id = :product_id"),
            {"id": conversation_id, "product_id": product_id},
        ).first()
        if row:
            db.execute(
                text("UPDATE conversations SET updated_at = now() WHERE id = :id"),
                {"id": conversation_id},
            )
            db.commit()
            return conversation_id

    row = db.execute(
        text("""
            SELECT id FROM conversations
            WHERE user_id = :user_id AND repo_name = :repo_name AND product_id = :product_id
            ORDER BY updated_at DESC LIMIT 1
        """),
        {"user_id": user.id, "repo_name": repo_name, "product_id": product_id},
    ).mappings().first()

    if row:
        db.execute(
            text("UPDATE conversations SET updated_at = now() WHERE id = :id"),
            {"id": row["id"]},
        )
        db.commit()
        return row["id"]

    conv_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO conversations (id, org_id, product_id, repo_name, user_id, title)
            VALUES (:id, :org_id, :product_id, :repo_name, :user_id, :title)
        """),
        {
            "id": conv_id,
            "org_id": user.org_id,
            "product_id": product_id,
            "repo_name": repo_name,
            "user_id": user.id,
            "title": title,
        },
    )
    db.commit()
    return conv_id


def _save_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    sources: list | None = None,
    model_used: str | None = None,
    tokens_used: int | None = None,
    cost_usd: float | None = None,
):
    msg_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO messages (id, conversation_id, role, content, sources, model_used, tokens_used, cost_usd)
            VALUES (:id, :conversation_id, :role, :content, :sources, :model_used, :tokens_used, :cost_usd)
        """),
        {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": json.dumps(sources) if sources else None,
            "model_used": model_used,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
        },
    )
    db.commit()


def _search_knowledge(db: Session, question: str, product_id: str | None, top_k: int = 3) -> list[dict]:
    """Search knowledge_entries for relevant technical memory."""
    try:
        from app.core.embedder import Embedder
        embedder = Embedder()
        query_embedding = embedder.embed_text(question)

        rows = db.execute(
            text("""
                SELECT id, title, summary, source_type, source_url,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM knowledge_entries
                WHERE product_id = :product_id AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {"product_id": product_id, "embedding": str(query_embedding), "top_k": top_k},
        ).mappings().all()

        # Filter by minimum relevance threshold
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "summary": r["summary"] or "",
                "source_type": r["source_type"],
                "source_url": r.get("source_url"),
                "score": float(r["score"]),
            }
            for r in rows
            if float(r["score"]) > 0.3
        ]
    except Exception as e:
        logger.debug(f"Knowledge search skipped: {e}")
        return []


def _has_llm_providers(db: Session, org_id: str) -> bool:
    """Check if org has any active LLM providers configured."""
    try:
        count = db.execute(
            text("SELECT COUNT(*) FROM llm_providers WHERE org_id = :org_id AND is_active = true"),
            {"org_id": org_id},
        ).scalar()
        return count > 0
    except Exception:
        return False


def _generate_stream(question: str, repo_name: str, max_chunks: int, provider_id: str | None, db: Session, user: User, conversation_id: str | None = None, product_id: str | None = None):
    try:
        assistant = Assistant(db)
        chunks = assistant._search.search(question, repo_name, top_k=max_chunks, org_id=user.org_id, product_id=product_id)
    except Exception as e:
        logger.error(f"Erro na busca: {e}", exc_info=True)
        yield _sse_event({"type": "error", "message": f"Erro na busca: {e}"})
        return

    # Search knowledge entries in parallel
    knowledge_results = _search_knowledge(db, question, product_id, top_k=3)

    try:
        # Get or create conversation + save user message
        conv_id = _get_or_create_conversation(db, user, repo_name, question[:100], conversation_id, product_id=product_id)
        _save_message(db, conv_id, "user", question)
    except Exception as e:
        logger.error(f"Erro ao salvar conversa: {e}", exc_info=True)
        yield _sse_event({"type": "error", "message": f"Erro ao salvar conversa: {e}"})
        return

    # Emit conversation_id so frontend can track it
    yield _sse_event({"type": "conversation", "conversation_id": conv_id})

    if not chunks and not knowledge_results:
        no_result_msg = "Nao encontrei nenhum trecho de codigo indexado para esse repositorio. Verifique se a ingestao foi realizada."
        yield _sse_event({"type": "text", "content": no_result_msg})
        yield _sse_event({"type": "done", "tokens": 0, "cost_usd": 0, "model": "none"})
        _save_message(db, conv_id, "assistant", no_result_msg, model_used="none", tokens_used=0, cost_usd=0)
        return

    sources = [
        {
            "file_path": c["file_path"],
            "chunk_name": c["chunk_name"],
            "chunk_type": c["chunk_type"],
            "content_preview": c["content"][:200],
            "start_line": c.get("start_line"),
        }
        for c in chunks
    ]

    # Add knowledge sources
    knowledge_sources = [
        {
            "title": k["title"],
            "summary": k["summary"][:200],
            "source_type": k["source_type"],
            "source_url": k.get("source_url"),
        }
        for k in knowledge_results
    ]

    yield _sse_event({"type": "sources", "sources": sources, "knowledge_sources": knowledge_sources})

    # Build user message with both code chunks and knowledge context
    user_message = assistant._build_user_message(question, chunks)

    if knowledge_results:
        knowledge_context = "\n\n--- MEMORIA TECNICA ---\n"
        for k in knowledge_results:
            knowledge_context += f"\n[{k['source_type'].upper()}] {k['title']}\n{k['summary'][:500]}\n"
        user_message += knowledge_context

    # Role-based provider selection:
    # - suporte: always uses default (ignore provider_id)
    # - dev/admin: can specify provider_id
    effective_provider_id = None
    if user.role in ("admin", "dev"):
        effective_provider_id = provider_id

    # Try new LLM Router (llm_providers table) first
    use_router = _has_llm_providers(db, user.org_id)

    if use_router:
        full_response = ""
        final_meta = None

        try:
            for text_chunk, meta in llm_router.stream(
                db=db,
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                org_id=user.org_id,
                provider_id=effective_provider_id,
            ):
                if text_chunk:
                    full_response += text_chunk
                    yield _sse_event({"type": "text", "content": text_chunk})
                if meta:
                    final_meta = meta
                    yield _sse_event({
                        "type": "done",
                        "tokens": meta["tokens"],
                        "cost_usd": meta["cost_usd"],
                        "model": meta["model"],
                        "provider_name": meta.get("provider_name", ""),
                        "provider": meta.get("provider", ""),
                    })
        except Exception as e:
            logger.error(f"Erro no streaming (router): {e}")
            yield _sse_event({"type": "error", "message": str(e)})

        if full_response:
            _save_message(
                db,
                conv_id,
                "assistant",
                full_response,
                sources=sources,
                model_used=final_meta["model"] if final_meta else "unknown",
                tokens_used=final_meta["tokens"] if final_meta else None,
                cost_usd=final_meta["cost_usd"] if final_meta else None,
            )
        return

    # Fallback: legacy llm_client (env-based provider config)
    provider = settings.llm_provider.lower()
    has_key = (
        (provider == "openai" and settings.openai_api_key)
        or (provider == "anthropic" and settings.anthropic_api_key)
    )
    if not has_key:
        summary = "\n".join(
            f"- **{c['chunk_type']}** `{c['chunk_name']}` em `{c['file_path']}`"
            for c in chunks
        )
        fallback_msg = f"[Modo search-only — LLM nao configurado]\n\nChunks encontrados:\n{summary}"
        yield _sse_event({"type": "text", "content": fallback_msg})
        yield _sse_event({"type": "done", "tokens": 0, "cost_usd": 0, "model": "search-only"})
        _save_message(db, conv_id, "assistant", fallback_msg, sources=sources, model_used="search-only", tokens_used=0, cost_usd=0)
        return

    model, reason = assistant._select_model(question)

    full_response = ""
    final_meta = None

    try:
        for text_chunk, meta in stream_llm(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            model=model,
        ):
            if text_chunk:
                full_response += text_chunk
                yield _sse_event({"type": "text", "content": text_chunk})
            if meta:
                final_meta = meta
                yield _sse_event({
                    "type": "done",
                    "tokens": meta["tokens"],
                    "cost_usd": meta["cost_usd"],
                    "model": meta["model"],
                })
    except Exception as e:
        logger.error(f"Erro no streaming: {e}")
        yield _sse_event({"type": "error", "message": str(e)})

    if full_response:
        _save_message(
            db,
            conv_id,
            "assistant",
            full_response,
            sources=sources,
            model_used=final_meta["model"] if final_meta else model,
            tokens_used=final_meta["tokens"] if final_meta else None,
            cost_usd=final_meta["cost_usd"] if final_meta else None,
        )


def _safe_stream(generator):
    """Wrap generator to catch unhandled exceptions and emit them as SSE errors."""
    try:
        yield from generator
    except Exception as e:
        logger.error(f"Erro nao tratado no stream: {e}", exc_info=True)
        yield _sse_event({"type": "error", "message": f"Erro interno: {e}"})


@router.post("/ask/stream")
@limiter.limit(ASK_LIMIT)
def ask_stream(
    request: Request,
    body: StreamAskRequest,
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    return StreamingResponse(
        _safe_stream(_generate_stream(body.question, body.repo_name, body.max_chunks, body.provider_id, db, user, body.conversation_id, product_id=product.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
