import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi import Depends

# Configure logging so background tasks output is visible
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

from app.api.deps import get_current_product, get_current_user, get_data_session, get_session
from app.api.routes import admin, ask, ask_stream, audit, auth, codegen, conversations, docs, enterprise, executive, exports, health_admin, impact, incidents, ingest, integrations, knowledge, llm_providers, logs_ingest, monitor, notifications, onboarding, plans, products, reviews, rules, search, security, users, webhooks
from app.models.product import Product
from mcp.server import router as mcp_router, token_router as mcp_token_router
from app.db.session import SessionLocal, engine
from app.models.user import User
from app.core.rate_limit import limiter

app = FastAPI(
    title="Memora",
    description="Inteligência Técnica Operacional — Assistente de suporte baseado no codebase",
    version="0.2.0",
)

# --- Rate limiting ---
app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Limite de requisições excedido. Tente novamente em alguns instantes."},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

from app.config import settings as _settings


# --- Security headers middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if _settings.app_env != "development":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        return response


# --- Payload size limit middleware ---
_MAX_BODY_DEFAULT = 10 * 1024 * 1024  # 10MB
_MAX_BODY_INGEST = 50 * 1024 * 1024   # 50MB for file uploads
_MAX_BODY_CHAT = 1 * 1024 * 1024      # 1MB for ask/chat

_INGEST_PATHS = {"/api/ingest", "/api/ingest/stream", "/api/knowledge/documents"}
_CHAT_PATHS = {"/api/ask", "/api/ask/stream"}


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            length = int(content_length)
            path = request.url.path

            if path in _CHAT_PATHS and length > _MAX_BODY_CHAT:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload excede o limite de 1MB para esta rota."},
                )
            elif path in _INGEST_PATHS and length > _MAX_BODY_INGEST:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload excede o limite de 50MB para upload."},
                )
            elif length > _MAX_BODY_DEFAULT:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload excede o limite de 10MB."},
                )

        return await call_next(request)


# --- Plan enforcement middleware ---
# Routes exempt from plan check (always accessible)
_PLAN_EXEMPT_PREFIXES = (
    "/api/auth/", "/api/health", "/api/enterprise/",
    "/api/admin/plan", "/api/postmortem/",
    "/api/webhooks/", "/api/logs/ingest",
    "/mcp/",
)
_PLAN_EXEMPT_EXACT = {"/api/health", "/api/health/admin-exists", "/api/health/admin"}


class PlanEnforcementMiddleware(BaseHTTPMiddleware):
    """Bloqueia rotas de dados se o plano estiver expirado/inativo."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip non-API routes, exempt routes, and OPTIONS
        if request.method == "OPTIONS":
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        if path in _PLAN_EXEMPT_EXACT:
            return await call_next(request)
        if any(path.startswith(p) for p in _PLAN_EXEMPT_PREFIXES):
            return await call_next(request)

        # Extract JWT to identify org — only if Authorization header present
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        try:
            from app.core.auth import decode_supabase_jwt
            payload = decode_supabase_jwt(auth_header[7:])
            if not payload:
                return await call_next(request)

            user_id = payload.get("sub")
            if not user_id:
                return await call_next(request)

            db = SessionLocal()
            try:
                user_row = db.execute(
                    text("SELECT org_id FROM users WHERE id = :uid AND is_active = true"),
                    {"uid": user_id},
                ).mappings().first()
                if not user_row:
                    return await call_next(request)

                plan_row = db.execute(
                    text("SELECT * FROM org_plans WHERE org_id = :oid ORDER BY created_at DESC LIMIT 1"),
                    {"oid": user_row["org_id"]},
                ).mappings().first()

                if not plan_row:
                    # Org sem plano (legado) — permitir acesso
                    return await call_next(request)

                from datetime import datetime
                now = datetime.utcnow()
                is_blocked = False

                if not plan_row["is_active"]:
                    is_blocked = True
                elif plan_row["plan"] == "pro_trial" and plan_row["trial_ends_at"]:
                    if now > plan_row["trial_ends_at"]:
                        is_blocked = True

                if is_blocked:
                    return JSONResponse(
                        status_code=402,
                        content={
                            "error": "plan_expired",
                            "message": "Seu trial de 7 dias expirou.",
                            "upgrade_url": "/upgrade",
                        },
                    )
            finally:
                db.close()
        except Exception:
            pass  # On error, let the request through

        return await call_next(request)


# Add middlewares (order matters — last added = first executed)
app.add_middleware(PlanEnforcementMiddleware)
app.add_middleware(PayloadSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
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
app.include_router(audit.router, prefix="/api", tags=["audit"])
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
app.include_router(notifications.digest_router, prefix="/api", tags=["digest"])
app.include_router(onboarding.router, prefix="/api", tags=["onboarding"])
app.include_router(products.router, prefix="/api", tags=["products"])
app.include_router(enterprise.router, prefix="/api", tags=["enterprise"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(exports.router, prefix="/api", tags=["exports"])
app.include_router(plans.router, prefix="/api", tags=["plans"])
app.include_router(health_admin.router, prefix="/api", tags=["health"])
app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
app.include_router(mcp_token_router, prefix="/api", tags=["mcp"])


# Iniciar schedulers em background
from app.core.enterprise_health_scheduler import start_scheduler as _start_enterprise_health
_start_enterprise_health()

from app.core.scheduler import start_scheduler as _start_main_scheduler
_start_main_scheduler()


# Validar encryption key na inicializacao (apenas em producao — em dev/test pode nao estar configurada)
if _settings.app_env not in ("development", "test"):
    from app.core.encryption import validate_encryption_key
    validate_encryption_key()


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
    db=Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    from sqlalchemy import text as sql_text

    rows = db.execute(sql_text("""
        SELECT
            repo_name as name,
            COUNT(*) as chunks_count,
            MAX(created_at) as last_indexed
        FROM code_chunks
        WHERE product_id = :product_id
        GROUP BY repo_name
        ORDER BY repo_name
    """), {"product_id": product.id}).mappings().all()
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
