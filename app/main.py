import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from fastapi import Depends

# Configure logging so background tasks output is visible
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

from app.api.deps import get_current_user, get_session
from app.api.routes import admin, ask, ask_stream, auth, codegen, conversations, docs, executive, health_admin, impact, incidents, ingest, integrations, knowledge, llm_providers, logs_ingest, monitor, notifications, onboarding, reviews, rules, security, users, webhooks
from mcp.server import router as mcp_router, token_router as mcp_token_router
from app.db.session import SessionLocal, engine
from app.models.user import User

app = FastAPI(
    title="Memora",
    description="Inteligência Técnica Operacional — Assistente de suporte baseado no codebase",
    version="0.2.0",
)

from app.config import settings as _settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(ask.router, prefix="/api", tags=["ask"])
app.include_router(ask_stream.router, prefix="/api", tags=["ask-stream"])
app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(integrations.router, prefix="/api", tags=["integrations"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(llm_providers.router, prefix="/api", tags=["llm-providers"])
app.include_router(llm_providers.active_router, prefix="/api", tags=["llm-providers"])
app.include_router(logs_ingest.router, prefix="/api", tags=["logs"])
app.include_router(monitor.router, prefix="/api", tags=["monitor"])
app.include_router(knowledge.router, prefix="/api", tags=["knowledge"])
app.include_router(knowledge.public_router, prefix="/api", tags=["knowledge"])
app.include_router(reviews.router, prefix="/api", tags=["reviews"])
app.include_router(docs.router, prefix="/api", tags=["docs"])
app.include_router(docs.public_router, prefix="/api", tags=["docs"])
app.include_router(rules.router, prefix="/api", tags=["rules"])
app.include_router(rules.public_router, prefix="/api", tags=["rules"])
app.include_router(codegen.router, prefix="/api", tags=["codegen"])
app.include_router(incidents.router, prefix="/api", tags=["incidents"])
app.include_router(incidents.public_router, tags=["incidents"])
app.include_router(impact.router, prefix="/api", tags=["impact"])
app.include_router(executive.router, prefix="/api", tags=["executive"])
app.include_router(security.router, prefix="/api", tags=["security"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(onboarding.router, prefix="/api", tags=["onboarding"])
app.include_router(health_admin.router, prefix="/api", tags=["health"])
app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
app.include_router(mcp_token_router, prefix="/api", tags=["mcp"])


@app.get("/api/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {"status": "ok", "database": db_status, "version": "0.2.0"}


@app.get("/api/repos")
def list_repos(
    db=Depends(get_session),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import text as sql_text

    rows = db.execute(sql_text("""
        SELECT
            repo_name as name,
            COUNT(*) as chunks_count,
            MAX(created_at) as last_indexed
        FROM code_chunks
        WHERE org_id = :org_id
        GROUP BY repo_name
        ORDER BY repo_name
    """), {"org_id": user.org_id}).mappings().all()
    return [
        {
            "name": r["name"],
            "chunks_count": r["chunks_count"],
            "last_indexed": str(r["last_indexed"]) if r["last_indexed"] else None,
            "status": "indexed",
        }
        for r in rows
    ]


@app.get("/api/health/admin-exists")
def admin_exists():
    db = SessionLocal()
    try:
        total = db.query(User).count()
        return {
            "exists": total > 0,
            "total_users": total,
            "requires_invite": total > 0,
        }
    finally:
        db.close()
