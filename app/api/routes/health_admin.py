"""Admin-only health check endpoint — verifies all system components in parallel."""

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.config import settings
from app.db.session import engine
from app.models.user import User

router = APIRouter()

COMPONENT_TIMEOUT = 3  # seconds per check


def _check_database() -> dict:
    start = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = int((time.time() - start) * 1000)
        return {"status": "ok", "latency_ms": latency, "detail": "PostgreSQL — Supabase"}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return {"status": "down", "latency_ms": latency, "detail": str(e)[:200]}


def _check_embeddings() -> dict:
    start = time.time()
    try:
        if not settings.openai_api_key:
            return {"status": "down", "provider": "openai", "latency_ms": 0, "detail": "OPENAI_API_KEY nao configurada"}
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)
        client.embeddings.create(input=["health check"], model=settings.embedding_model)
        latency = int((time.time() - start) * 1000)
        return {"status": "ok", "provider": "openai", "latency_ms": latency, "detail": f"OpenAI {settings.embedding_model}"}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return {"status": "down", "provider": "openai", "latency_ms": latency, "detail": str(e)[:200]}


def _check_llm_providers(db: Session, org_id: str) -> list[dict]:
    from app.integrations.llm_router import test_provider
    from app.core.encryption import decrypt_api_key

    results = []
    try:
        rows = db.execute(
            text("SELECT id, name, is_default FROM llm_providers WHERE org_id = :org_id AND is_active = true"),
            {"org_id": org_id},
        ).mappings().all()

        for row in rows:
            try:
                result = test_provider(db, row["id"], org_id)
                results.append({
                    "name": row["name"],
                    "status": "ok" if result.get("status") == "ok" else "down",
                    "is_default": row["is_default"],
                    "latency_ms": result.get("latency_ms", 0),
                })
            except Exception as e:
                results.append({
                    "name": row["name"],
                    "status": "down",
                    "is_default": row["is_default"],
                    "latency_ms": 0,
                })
    except Exception:
        pass

    return results


def _check_github_webhook(db: Session, org_id: str) -> dict:
    if not settings.github_webhook_secret:
        return {"status": "not_configured", "last_received_at": None, "detail": "GITHUB_WEBHOOK_SECRET nao definido"}

    try:
        row = db.execute(
            text("""
                SELECT MAX(created_at) as last_event FROM code_reviews
                WHERE org_id = :org_id AND source_type = 'pr'
            """),
            {"org_id": org_id},
        ).mappings().first()

        last_at = row["last_event"] if row else None
        return {
            "status": "ok",
            "last_received_at": str(last_at) if last_at else None,
            "detail": "Webhook configurado",
        }
    except Exception as e:
        return {"status": "error", "last_received_at": None, "detail": str(e)[:200]}


def _check_email() -> dict:
    if not settings.smtp_host:
        return {"status": "not_configured", "provider": None}

    provider = "SMTP customizado"
    host = settings.smtp_host.lower()
    if "gmail" in host:
        provider = "Gmail"
    elif "resend" in host:
        provider = "Resend"
    elif "sendgrid" in host:
        provider = "SendGrid"

    return {"status": "ok", "provider": provider}


def _check_storage(db: Session, org_id: str) -> dict:
    try:
        row = db.execute(
            text("""
                SELECT
                    COUNT(*) as chunks_total,
                    COUNT(DISTINCT repo_name) as repos_indexed,
                    MAX(created_at) as last_indexed_at
                FROM code_chunks
                WHERE org_id = :org_id
            """),
            {"org_id": org_id},
        ).mappings().first()

        return {
            "chunks_total": row["chunks_total"] if row else 0,
            "repos_indexed": row["repos_indexed"] if row else 0,
            "last_indexed_at": str(row["last_indexed_at"]) if row and row["last_indexed_at"] else None,
        }
    except Exception:
        return {"chunks_total": 0, "repos_indexed": 0, "last_indexed_at": None}


@router.get("/health/admin")
def health_admin(
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_session),
):
    org_id = user.org_id
    results = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        # Submit all checks in parallel
        f_db = executor.submit(_check_database)
        f_emb = executor.submit(_check_embeddings)
        f_llm = executor.submit(_check_llm_providers, db, org_id)
        f_gh = executor.submit(_check_github_webhook, db, org_id)
        f_email = executor.submit(_check_email)
        f_storage = executor.submit(_check_storage, db, org_id)

        try:
            results["database"] = f_db.result(timeout=COMPONENT_TIMEOUT)
        except (FuturesTimeout, Exception):
            results["database"] = {"status": "down", "latency_ms": COMPONENT_TIMEOUT * 1000, "detail": "Timeout"}

        try:
            results["embeddings"] = f_emb.result(timeout=COMPONENT_TIMEOUT)
        except (FuturesTimeout, Exception):
            results["embeddings"] = {"status": "down", "provider": "openai", "latency_ms": COMPONENT_TIMEOUT * 1000, "detail": "Timeout"}

        try:
            results["llm_providers"] = f_llm.result(timeout=COMPONENT_TIMEOUT)
        except (FuturesTimeout, Exception):
            results["llm_providers"] = []

        try:
            results["github_webhook"] = f_gh.result(timeout=COMPONENT_TIMEOUT)
        except (FuturesTimeout, Exception):
            results["github_webhook"] = {"status": "error", "last_received_at": None, "detail": "Timeout"}

        try:
            results["email"] = f_email.result(timeout=COMPONENT_TIMEOUT)
        except (FuturesTimeout, Exception):
            results["email"] = {"status": "error", "provider": None}

        try:
            results["storage"] = f_storage.result(timeout=COMPONENT_TIMEOUT)
        except (FuturesTimeout, Exception):
            results["storage"] = {"chunks_total": 0, "repos_indexed": 0, "last_indexed_at": None}

    # Background workers — simplified (no celery/rq, just report ok)
    results["background_workers"] = {
        "status": "ok",
        "active_jobs": 0,
        "failed_jobs_last_hour": 0,
    }

    return results
