"""Endpoint de ingestao de logs via token de projeto (sem JWT)."""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_data_session
from app.core.log_analyzer import analyze
from app.core.notifier import notify_alert

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_LEVELS = {"debug", "info", "warning", "error", "critical"}


class SingleLogPayload(BaseModel):
    level: str
    message: str
    source: str | None = None
    stack_trace: str | None = None
    occurred_at: str | None = None
    metadata: dict | None = None


class BatchLogPayload(BaseModel):
    logs: list[SingleLogPayload] | None = None
    # Also accept single log fields at top level
    level: str | None = None
    message: str | None = None
    source: str | None = None
    stack_trace: str | None = None
    occurred_at: str | None = None
    metadata: dict | None = None


def _authenticate_project(authorization: str | None = Header(None), db: Session = Depends(get_data_session)):
    """Authenticate by project token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de projeto obrigatorio")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token de projeto obrigatorio")

    project = db.execute(
        text("SELECT id, org_id, is_active FROM monitored_projects WHERE token = :token"),
        {"token": token},
    ).mappings().first()

    if not project:
        raise HTTPException(status_code=401, detail="Token de projeto invalido")
    if not project["is_active"]:
        raise HTTPException(status_code=403, detail="Projeto desativado")

    return dict(project)


def _insert_log(db: Session, project_id: str, org_id: str, log: SingleLogPayload) -> tuple[str, bool]:
    """Insert a log entry. Returns (log_id, needs_analysis)."""
    level = log.level.lower()
    if level not in VALID_LEVELS:
        level = "info"

    occurred_at = None
    if log.occurred_at:
        try:
            occurred_at = datetime.fromisoformat(log.occurred_at.replace("Z", "+00:00"))
        except ValueError:
            pass

    log_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO log_entries
                (id, project_id, org_id, level, message, source, stack_trace, metadata,
                 occurred_at, raw_payload)
            VALUES
                (:id, :project_id, :org_id, :level, :message, :source, :stack_trace, :metadata,
                 :occurred_at, :raw_payload)
        """),
        {
            "id": log_id,
            "project_id": project_id,
            "org_id": org_id,
            "level": level,
            "message": log.message[:10000],
            "source": (log.source or "")[:500] or None,
            "stack_trace": log.stack_trace,
            "metadata": str(log.metadata) if log.metadata else None,
            "occurred_at": occurred_at,
            "raw_payload": log.model_dump_json(),
        },
    )

    needs_analysis = level in ("error", "critical")
    return log_id, needs_analysis


def _analyze_and_notify(log_id: str, org_id: str):
    """Background task: analyze log and send notifications."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        alert_id = analyze(db, log_id, org_id)
        if alert_id:
            notify_alert(db, alert_id)
    except Exception as e:
        logger.error("Erro na analise background do log %s: %s", log_id, e)
    finally:
        db.close()


@router.post("/logs/ingest")
def ingest_logs(
    body: BatchLogPayload,
    background_tasks: BackgroundTasks,
    project: dict = Depends(_authenticate_project),
    db: Session = Depends(get_data_session),
):
    """Receive logs from external systems. Authenticates via project token."""
    project_id = project["id"]
    org_id = project["org_id"]

    logs_to_insert: list[SingleLogPayload] = []

    if body.logs:
        logs_to_insert = body.logs
    elif body.level and body.message:
        logs_to_insert = [SingleLogPayload(
            level=body.level,
            message=body.message,
            source=body.source,
            stack_trace=body.stack_trace,
            occurred_at=body.occurred_at,
            metadata=body.metadata,
        )]
    else:
        raise HTTPException(status_code=400, detail="Payload invalido: envie 'level'+'message' ou 'logs'")

    queued = 0
    for log in logs_to_insert:
        log_id, needs_analysis = _insert_log(db, project_id, org_id, log)
        if needs_analysis:
            background_tasks.add_task(_analyze_and_notify, log_id, org_id)
            queued += 1

    db.commit()

    # Update project updated_at
    db.execute(
        text("UPDATE monitored_projects SET updated_at = now() WHERE id = :id"),
        {"id": project_id},
    )
    db.commit()

    return {"received": len(logs_to_insert), "queued_for_analysis": queued}
