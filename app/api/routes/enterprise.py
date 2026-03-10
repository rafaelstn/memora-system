"""Rotas do modo Enterprise — configuracao e setup do banco do cliente."""

import json
import logging
import queue
import threading

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_session, invalidate_org_mode_cache, require_role
from app.core.enterprise_db import (
    check_health,
    get_health_log,
    get_setup_status,
    invalidate_engine_cache,
    mark_setup_complete,
    run_migrations,
    save_config,
    test_connection,
)
from app.core.rate_limit import ENTERPRISE_LIMIT, limiter
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class DBConnectionRequest(BaseModel):
    host: str
    port: int = Field(default=5432)
    database: str
    username: str
    password: str
    ssl_mode: str = Field(default="require")


@router.post("/enterprise/test-connection")
@limiter.limit(ENTERPRISE_LIMIT)
def enterprise_test_connection(
    request: Request,
    body: DBConnectionRequest,
    user: User = Depends(require_role("admin")),
):
    """Testa conexao com o banco externo sem salvar credenciais."""
    result = test_connection(
        host=body.host,
        port=body.port,
        database=body.database,
        username=body.username,
        password=body.password,
        ssl_mode=body.ssl_mode,
    )
    return result


@router.post("/enterprise/setup")
def enterprise_setup(
    body: DBConnectionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Salva credenciais + executa migrations no banco do cliente via SSE."""
    org_id = user.org_id

    # Invalidar caches antes de re-setup
    invalidate_engine_cache(org_id)
    invalidate_org_mode_cache(org_id)

    # Salvar credenciais criptografadas
    save_config(
        org_id=org_id,
        host=body.host,
        port=body.port,
        database=body.database,
        username=body.username,
        password=body.password,
        ssl_mode=body.ssl_mode,
    )
    logger.info(f"Credenciais Enterprise salvas para org {org_id}")

    # Executar migrations em thread separada, SSE de progresso
    progress_queue: queue.Queue = queue.Queue()

    def run_setup():
        try:
            for event in run_migrations(
                host=body.host,
                port=body.port,
                database=body.database,
                username=body.username,
                password=body.password,
                ssl_mode=body.ssl_mode,
            ):
                progress_queue.put(event)

                if event.get("type") == "done" and event.get("success"):
                    mark_setup_complete(org_id)
                    logger.info(f"Setup Enterprise concluido para org {org_id}")

        except Exception as e:
            progress_queue.put({"type": "error", "message": str(e)})
        finally:
            progress_queue.put(None)  # sentinel

    thread = threading.Thread(target=run_setup, daemon=True)
    thread.start()

    def event_stream():
        while True:
            try:
                msg = progress_queue.get(timeout=120)
            except queue.Empty:
                break
            if msg is None:
                yield "data: [DONE]\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/enterprise/status")
def enterprise_status(
    user: User = Depends(require_role("admin")),
):
    """Retorna status do setup Enterprise da org."""
    return get_setup_status(user.org_id)


@router.post("/enterprise/health-check")
def enterprise_health_check(
    user: User = Depends(require_role("admin")),
):
    """Executa health check manual no banco Enterprise e notifica se houver transicao."""
    result = check_health(user.org_id)

    # Notificar por email em caso de transicao de status
    prev = result.get("previous_status")
    curr = result["status"]
    if prev and prev != curr:
        _notify_health_transition(user.org_id, curr, result.get("error"))

    return result


@router.get("/enterprise/health-log")
def enterprise_health_log_route(
    user: User = Depends(require_role("admin")),
    limit: int = Query(default=20, le=100),
):
    """Retorna historico de health checks do banco Enterprise."""
    return get_health_log(user.org_id, limit=limit)


def _notify_health_transition(org_id: str, new_status: str, error: str | None = None):
    """Envia email de notificacao quando status do banco muda."""
    try:
        from app.core.email_client import (
            build_enterprise_db_down_email,
            build_enterprise_db_recovered_email,
            send_to_org_admins,
        )
        from app.config import settings
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            # Buscar nome da org
            from sqlalchemy import text
            row = db.execute(
                text("SELECT name FROM organizations WHERE id = :org_id"),
                {"org_id": org_id},
            ).first()
            org_name = row[0] if row else org_id

            dashboard_url = f"{settings.app_url}/setup/enterprise"

            if new_status == "error":
                subject, body = build_enterprise_db_down_email(org_name, error or "Erro desconhecido", dashboard_url)
            else:
                subject, body = build_enterprise_db_recovered_email(org_name, dashboard_url)

            send_to_org_admins(db, org_id, subject, body)
            logger.info(f"Email de transicao Enterprise ({new_status}) enviado para org {org_id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Falha ao notificar transicao de health Enterprise: {e}")
