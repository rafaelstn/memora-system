"""Endpoints de gerenciamento do Monitor de Erros (admin + dev)."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.core.notifier import test_webhook as test_webhook_fn
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_role("admin", "dev"))])
logger = logging.getLogger(__name__)


def _get_user(user: User = Depends(require_role("admin", "dev"))) -> User:
    return user


# --- Projects ---

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


@router.get("/monitor/projects")
def list_projects(db: Session = Depends(get_session), user: User = Depends(_get_user)):
    org_id = user.org_id
    rows = db.execute(text("""
        SELECT
            mp.*,
            COALESCE(
                (SELECT COUNT(*) FROM log_entries le
                 WHERE le.project_id = mp.id AND le.received_at >= CURRENT_DATE), 0
            ) as logs_today,
            COALESCE(
                (SELECT COUNT(*) FROM error_alerts ea
                 WHERE ea.project_id = mp.id AND ea.status = 'open'), 0
            ) as open_alerts,
            (SELECT MAX(le2.received_at) FROM log_entries le2
             WHERE le2.project_id = mp.id) as last_log_at
        FROM monitored_projects mp
        WHERE mp.org_id = :org_id AND mp.is_active = true
        ORDER BY mp.created_at DESC
    """), {"org_id": org_id}).mappings().all()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "token_preview": r["token_preview"],
            "is_active": r["is_active"],
            "logs_today": r["logs_today"],
            "open_alerts": r["open_alerts"],
            "last_log_at": str(r["last_log_at"]) if r["last_log_at"] else None,
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


@router.post("/monitor/projects")
def create_project(body: ProjectCreate, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    project_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    token_preview = token[:8]

    db.execute(text("""
        INSERT INTO monitored_projects (id, org_id, name, description, token, token_preview, created_by)
        VALUES (:id, :org_id, :name, :description, :token, :token_preview, :created_by)
    """), {
        "id": project_id,
        "org_id": user.org_id,
        "name": body.name,
        "description": body.description,
        "token": token,
        "token_preview": token_preview,
        "created_by": user.id,
    })
    db.commit()

    return {
        "id": project_id,
        "name": body.name,
        "description": body.description,
        "token": token,
        "token_preview": token_preview,
    }


@router.delete("/monitor/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    result = db.execute(
        text("UPDATE monitored_projects SET is_active = false WHERE id = :id AND org_id = :org_id"),
        {"id": project_id, "org_id": user.org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado")
    return {"deleted": True}


@router.post("/monitor/projects/{project_id}/rotate-token")
def rotate_token(project_id: str, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    new_token = str(uuid.uuid4())
    result = db.execute(
        text("""
            UPDATE monitored_projects
            SET token = :token, token_preview = :preview, updated_at = now()
            WHERE id = :id AND org_id = :org_id AND is_active = true
        """),
        {"token": new_token, "preview": new_token[:8], "id": project_id, "org_id": user.org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado")
    return {"token": new_token, "token_preview": new_token[:8]}


@router.get("/monitor/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    row = db.execute(
        text("SELECT * FROM monitored_projects WHERE id = :id AND org_id = :org_id"),
        {"id": project_id, "org_id": user.org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Projeto nao encontrado")
    result = dict(row)
    result["created_at"] = str(result["created_at"]) if result.get("created_at") else None
    result["updated_at"] = str(result["updated_at"]) if result.get("updated_at") else None
    # Never expose full token via GET
    del result["token"]
    return result


# --- Alerts ---

@router.get("/monitor/alerts")
def list_alerts(
    project_id: str | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    org_id = user.org_id
    per_page = 50
    offset = (page - 1) * per_page

    query = """
        SELECT ea.*, mp.name as project_name
        FROM error_alerts ea
        JOIN monitored_projects mp ON mp.id = ea.project_id
        WHERE ea.org_id = :org_id
    """
    params: dict = {"org_id": org_id, "limit": per_page, "offset": offset}

    if project_id:
        query += " AND ea.project_id = :project_id"
        params["project_id"] = project_id
    if severity:
        query += " AND ea.severity = :severity"
        params["severity"] = severity
    if status:
        query += " AND ea.status = :status"
        params["status"] = status

    query += " ORDER BY ea.created_at DESC LIMIT :limit OFFSET :offset"

    rows = db.execute(text(query), params).mappings().all()

    return [
        {
            "id": r["id"],
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "title": r["title"],
            "severity": r["severity"],
            "affected_component": r["affected_component"],
            "status": r["status"],
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


@router.get("/monitor/alerts/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    alert = db.execute(
        text("""
            SELECT ea.*, mp.name as project_name
            FROM error_alerts ea
            JOIN monitored_projects mp ON mp.id = ea.project_id
            WHERE ea.id = :id AND ea.org_id = :org_id
        """),
        {"id": alert_id, "org_id": user.org_id},
    ).mappings().first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alerta nao encontrado")

    # Fetch associated log entry
    log_entry = db.execute(
        text("SELECT * FROM log_entries WHERE id = :id"),
        {"id": alert["log_entry_id"]},
    ).mappings().first()

    result = dict(alert)
    for k in ("created_at", "acknowledged_at", "resolved_at"):
        if result.get(k):
            result[k] = str(result[k])
    result["log_entry"] = dict(log_entry) if log_entry else None
    if result["log_entry"]:
        for k in ("received_at", "occurred_at"):
            if result["log_entry"].get(k):
                result["log_entry"][k] = str(result["log_entry"][k])
    return result


class AlertStatusUpdate(BaseModel):
    status: str


@router.patch("/monitor/alerts/{alert_id}/status")
def update_alert_status(
    alert_id: str,
    body: AlertStatusUpdate,
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    if body.status not in ("acknowledged", "resolved"):
        raise HTTPException(status_code=400, detail="Status invalido. Use: acknowledged, resolved")

    from app.core.query_builder import build_set_clause

    update_parts = ["status = :status"]
    params: dict = {"status": body.status, "id": alert_id, "org_id": user.org_id}

    if body.status == "acknowledged":
        update_parts += ["acknowledged_by = :user_id", "acknowledged_at = now()"]
        params["user_id"] = user.id
    elif body.status == "resolved":
        update_parts += ["resolved_by = :user_id", "resolved_at = now()"]
        params["user_id"] = user.id

    set_clause = build_set_clause("error_alerts", update_parts)
    result = db.execute(
        text(f"UPDATE error_alerts SET {set_clause} WHERE id = :id AND org_id = :org_id"),
        params,
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alerta nao encontrado")
    return {"updated": True}


# --- Logs ---

@router.get("/monitor/logs")
def list_logs(
    project_id: str | None = Query(None),
    level: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    org_id = user.org_id
    per_page = 50
    offset = (page - 1) * per_page

    query = "SELECT * FROM log_entries WHERE org_id = :org_id"
    params: dict = {"org_id": org_id, "limit": per_page, "offset": offset}

    if project_id:
        query += " AND project_id = :project_id"
        params["project_id"] = project_id
    if level:
        query += " AND level = :level"
        params["level"] = level
    if start_date:
        query += " AND received_at >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND received_at <= :end_date"
        params["end_date"] = end_date

    query += " ORDER BY received_at DESC LIMIT :limit OFFSET :offset"
    rows = db.execute(text(query), params).mappings().all()

    return [
        {
            "id": r["id"],
            "project_id": r["project_id"],
            "level": r["level"],
            "message": r["message"][:500],
            "source": r["source"],
            "received_at": str(r["received_at"]),
            "occurred_at": str(r["occurred_at"]) if r.get("occurred_at") else None,
            "is_analyzed": r["is_analyzed"],
            "stack_trace": r["stack_trace"],
            "metadata": r["metadata"],
        }
        for r in rows
    ]


# --- Webhooks ---

class WebhookCreate(BaseModel):
    name: str
    url: str


@router.get("/monitor/webhooks")
def list_webhooks(db: Session = Depends(get_session), user: User = Depends(_get_user)):
    rows = db.execute(
        text("SELECT * FROM alert_webhooks WHERE org_id = :org_id ORDER BY created_at DESC"),
        {"org_id": user.org_id},
    ).mappings().all()
    return [dict(r) | {"created_at": str(r["created_at"])} for r in rows]


@router.post("/monitor/webhooks")
def create_webhook(body: WebhookCreate, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    wh_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO alert_webhooks (id, org_id, name, url, created_by)
        VALUES (:id, :org_id, :name, :url, :created_by)
    """), {
        "id": wh_id,
        "org_id": user.org_id,
        "name": body.name,
        "url": body.url,
        "created_by": user.id,
    })
    db.commit()
    return {"id": wh_id, "name": body.name, "url": body.url}


@router.delete("/monitor/webhooks/{webhook_id}")
def delete_webhook(webhook_id: str, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    result = db.execute(
        text("DELETE FROM alert_webhooks WHERE id = :id AND org_id = :org_id"),
        {"id": webhook_id, "org_id": user.org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Webhook nao encontrado")
    return {"deleted": True}


@router.post("/monitor/webhooks/{webhook_id}/test")
def test_webhook_endpoint(webhook_id: str, db: Session = Depends(get_session), user: User = Depends(_get_user)):
    wh = db.execute(
        text("SELECT url FROM alert_webhooks WHERE id = :id AND org_id = :org_id"),
        {"id": webhook_id, "org_id": user.org_id},
    ).mappings().first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook nao encontrado")
    return test_webhook_fn(wh["url"])
