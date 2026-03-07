"""Rotas de gestao de incidentes."""
import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_role
from app.core import email_client
from app.models.user import User

router = APIRouter(prefix="/incidents")

# ---------- Schemas ----------


class DeclareIncidentRequest(BaseModel):
    alert_id: str | None = None
    project_id: str
    title: str | None = None
    description: str | None = None
    severity: str = "high"


class UpdateStatusRequest(BaseModel):
    status: str
    resolution_summary: str | None = None


class TimelineEventRequest(BaseModel):
    content: str
    event_type: str = "comment"  # action | update | comment


class UpdateHypothesisRequest(BaseModel):
    status: str  # confirmed | discarded


# ---------- Helpers ----------

VALID_TRANSITIONS = {
    "open": ["investigating"],
    "investigating": ["mitigated", "resolved"],
    "mitigated": ["resolved"],
}


def _notify_incident(db: Session, incident_id: str, event: str):
    """Send email/webhook notifications for incident events."""
    from app.core.notifier import _send_webhook

    inc = db.execute(
        text("""
            SELECT i.*, mp.name as project_name, u.name as declared_by_name
            FROM incidents i
            JOIN monitored_projects mp ON mp.id = i.project_id
            LEFT JOIN users u ON u.id = i.declared_by
            WHERE i.id = :id
        """),
        {"id": incident_id},
    ).mappings().first()
    if not inc:
        return

    from app.config import settings
    app_url = settings.app_url
    detail_url = f"{app_url}/dashboard/monitor/incidents/{incident_id}"

    # Build email using templates
    inc_dict = dict(inc)
    if event == "declared":
        subject, body_html = email_client.build_incident_declared_email(inc_dict, detail_url)
    elif event == "resolved":
        subject, body_html = email_client.build_incident_resolved_email(inc_dict, detail_url)
    else:
        subject, body_html = email_client.build_incident_declared_email(inc_dict, detail_url)

    email_client.send_to_org_admins(db, inc["org_id"], subject, body_html, "incident")

    # Also send to devs
    email_client.send_to_role(db, inc["org_id"], "dev", subject, body_html)

    # Webhooks
    webhooks = db.execute(
        text("SELECT url FROM alert_webhooks WHERE org_id = :org_id AND is_active = true"),
        {"org_id": inc["org_id"]},
    ).mappings().all()
    payload = {
        "event": f"incident.{event}",
        "incident_id": incident_id,
        "title": inc["title"],
        "severity": inc["severity"],
        "status": inc["status"],
        "project": inc.get("project_name", ""),
        "url": detail_url,
    }
    for wh in webhooks:
        _send_webhook(wh["url"], payload)


# ---------- Endpoints ----------


@router.post("")
def declare_incident(
    body: DeclareIncidentRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Declare a new incident."""
    if body.severity not in ("low", "medium", "high", "critical"):
        raise HTTPException(400, "Severidade invalida")

    incident_id = str(uuid.uuid4())
    title = body.title

    # If from alert, use alert data if title not provided
    if body.alert_id and not title:
        alert = db.execute(
            text("SELECT title FROM error_alerts WHERE id = :id AND org_id = :org_id"),
            {"id": body.alert_id, "org_id": user.org_id},
        ).mappings().first()
        if alert:
            title = alert["title"]

    if not title:
        title = "Incidente sem titulo"

    now = datetime.utcnow()
    db.execute(
        text("""
            INSERT INTO incidents
                (id, org_id, alert_id, project_id, title, description, severity,
                 status, declared_by, declared_at)
            VALUES
                (:id, :org_id, :alert_id, :project_id, :title, :description, :severity,
                 'open', :declared_by, :declared_at)
        """),
        {
            "id": incident_id,
            "org_id": user.org_id,
            "alert_id": body.alert_id,
            "project_id": body.project_id,
            "title": title,
            "description": body.description,
            "severity": body.severity,
            "declared_by": user.id,
            "declared_at": now,
        },
    )

    # First timeline event
    db.execute(
        text("""
            INSERT INTO incident_timeline
                (id, incident_id, org_id, event_type, content, created_by)
            VALUES (:id, :incident_id, :org_id, 'declared', :content, :created_by)
        """),
        {
            "id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "org_id": user.org_id,
            "content": f"Incidente declarado por {user.name} as {now.strftime('%H:%M')}",
            "created_by": user.id,
        },
    )
    db.commit()

    # Background: generate hypotheses + notify
    bg.add_task(_run_hypothesis_generation, db, incident_id, user.org_id)
    bg.add_task(_notify_incident, db, incident_id, "declared")

    return {
        "id": incident_id,
        "title": title,
        "severity": body.severity,
        "status": "open",
        "declared_at": now.isoformat(),
    }


def _run_hypothesis_generation(db: Session, incident_id: str, org_id: str):
    from app.core.incident_analyzer import IncidentAnalyzer
    try:
        analyzer = IncidentAnalyzer(db, org_id)
        analyzer.generate_hypotheses(incident_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Falha ao gerar hipoteses: %s", e)


@router.get("")
def list_incidents(
    status: str | None = None,
    project_id: str | None = None,
    page: int = 1,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """List incidents with optional filters."""
    conditions = ["i.org_id = :org_id"]
    params: dict = {"org_id": user.org_id}

    if status:
        conditions.append("i.status = :status")
        params["status"] = status
    if project_id:
        conditions.append("i.project_id = :project_id")
        params["project_id"] = project_id

    where = " AND ".join(conditions)
    limit = 20
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    rows = db.execute(
        text(f"""
            SELECT i.*, mp.name as project_name, u.name as declared_by_name
            FROM incidents i
            JOIN monitored_projects mp ON mp.id = i.project_id
            LEFT JOIN users u ON u.id = i.declared_by
            WHERE {where}
            ORDER BY i.declared_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).mappings().all()

    total_row = db.execute(
        text(f"SELECT COUNT(*) as cnt FROM incidents i WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    ).mappings().first()

    return {
        "incidents": [dict(r) for r in rows],
        "total": total_row["cnt"] if total_row else 0,
        "page": page,
    }


@router.post("/watchdog/check")
def trigger_watchdog(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Manually trigger the stale incident watchdog."""
    from app.core.incident_watchdog import check_stale_incidents
    sent = check_stale_incidents(db)
    return {"reminders_sent": sent}


@router.get("/stats")
def incident_stats(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Return incident statistics with enhanced metrics."""
    stats = db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE status IN ('open', 'investigating')) as active,
                COUNT(*) FILTER (WHERE status = 'resolved'
                    AND resolved_at >= now() - INTERVAL '30 days') as resolved_month,
                COUNT(*) as total,
                AVG(EXTRACT(EPOCH FROM (resolved_at - declared_at)) / 3600)
                    FILTER (WHERE status = 'resolved') as avg_hours,
                AVG(EXTRACT(EPOCH FROM (resolved_at - declared_at)) / 3600)
                    FILTER (WHERE status = 'resolved'
                        AND resolved_at >= now() - INTERVAL '7 days') as avg_hours_7d,
                AVG(EXTRACT(EPOCH FROM (resolved_at - declared_at)) / 3600)
                    FILTER (WHERE status = 'resolved'
                        AND resolved_at >= now() - INTERVAL '30 days'
                        AND resolved_at < now() - INTERVAL '7 days') as avg_hours_prev
            FROM incidents
            WHERE org_id = :org_id
        """),
        {"org_id": user.org_id},
    ).mappings().first()

    # Most affected project
    most_affected = db.execute(
        text("""
            SELECT mp.name, COUNT(*) as cnt
            FROM incidents i
            JOIN monitored_projects mp ON mp.id = i.project_id
            WHERE i.org_id = :org_id AND i.declared_at >= now() - INTERVAL '30 days'
            GROUP BY mp.name
            ORDER BY cnt DESC
            LIMIT 1
        """),
        {"org_id": user.org_id},
    ).mappings().first()

    avg_hours = round(float(stats["avg_hours"]), 1) if stats and stats["avg_hours"] else None
    avg_hours_7d = round(float(stats["avg_hours_7d"]), 1) if stats and stats["avg_hours_7d"] else None
    avg_hours_prev = round(float(stats["avg_hours_prev"]), 1) if stats and stats["avg_hours_prev"] else None

    # MTTR trend: compare last 7d vs previous period
    mttr_trend = None
    if avg_hours_7d is not None and avg_hours_prev is not None and avg_hours_prev > 0:
        mttr_trend = round(((avg_hours_7d - avg_hours_prev) / avg_hours_prev) * 100, 1)

    return {
        "active": stats["active"] if stats else 0,
        "resolved_month": stats["resolved_month"] if stats else 0,
        "total": stats["total"] if stats else 0,
        "avg_resolution_hours": avg_hours,
        "avg_resolution_hours_7d": avg_hours_7d,
        "mttr_trend": mttr_trend,
        "most_affected_project": most_affected["name"] if most_affected else None,
        "most_affected_count": most_affected["cnt"] if most_affected else 0,
    }


@router.get("/{incident_id}")
def get_incident(
    incident_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Get incident detail with timeline and hypotheses."""
    inc = db.execute(
        text("""
            SELECT i.*, mp.name as project_name, u.name as declared_by_name
            FROM incidents i
            JOIN monitored_projects mp ON mp.id = i.project_id
            LEFT JOIN users u ON u.id = i.declared_by
            WHERE i.id = :id AND i.org_id = :org_id
        """),
        {"id": incident_id, "org_id": user.org_id},
    ).mappings().first()

    if not inc:
        raise HTTPException(404, "Incidente nao encontrado")

    timeline = db.execute(
        text("""
            SELECT t.*, u.name as author_name
            FROM incident_timeline t
            LEFT JOIN users u ON u.id = t.created_by
            WHERE t.incident_id = :id
            ORDER BY t.created_at ASC
        """),
        {"id": incident_id},
    ).mappings().all()

    hypotheses = db.execute(
        text("""
            SELECT h.*, u.name as confirmed_by_name
            FROM incident_hypotheses h
            LEFT JOIN users u ON u.id = h.confirmed_by
            WHERE h.incident_id = :id
            ORDER BY h.confidence DESC
        """),
        {"id": incident_id},
    ).mappings().all()

    return {
        **dict(inc),
        "timeline": [dict(t) for t in timeline],
        "hypotheses": [dict(h) for h in hypotheses],
    }


@router.get("/{incident_id}/timeline")
def get_timeline(
    incident_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """List timeline events for an incident."""
    # Verify access
    inc = db.execute(
        text("SELECT id FROM incidents WHERE id = :id AND org_id = :org_id"),
        {"id": incident_id, "org_id": user.org_id},
    ).mappings().first()
    if not inc:
        raise HTTPException(404, "Incidente nao encontrado")

    events = db.execute(
        text("""
            SELECT t.*, u.name as author_name
            FROM incident_timeline t
            LEFT JOIN users u ON u.id = t.created_by
            WHERE t.incident_id = :id
            ORDER BY t.created_at ASC
        """),
        {"id": incident_id},
    ).mappings().all()

    return {"events": [dict(e) for e in events]}


@router.post("/{incident_id}/timeline")
def add_timeline_event(
    incident_id: str,
    body: TimelineEventRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Add an event to the incident timeline."""
    if body.event_type not in ("action", "update", "comment"):
        raise HTTPException(400, "Tipo de evento invalido")

    inc = db.execute(
        text("SELECT id FROM incidents WHERE id = :id AND org_id = :org_id"),
        {"id": incident_id, "org_id": user.org_id},
    ).mappings().first()
    if not inc:
        raise HTTPException(404, "Incidente nao encontrado")

    event_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO incident_timeline
                (id, incident_id, org_id, event_type, content, created_by)
            VALUES (:id, :incident_id, :org_id, :event_type, :content, :created_by)
        """),
        {
            "id": event_id,
            "incident_id": incident_id,
            "org_id": user.org_id,
            "event_type": body.event_type,
            "content": body.content,
            "created_by": user.id,
        },
    )
    db.commit()

    return {"id": event_id, "event_type": body.event_type, "content": body.content}


@router.patch("/{incident_id}/status")
def update_status(
    incident_id: str,
    body: UpdateStatusRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Update incident status with valid transitions."""
    inc = db.execute(
        text("SELECT id, status, org_id FROM incidents WHERE id = :id AND org_id = :org_id"),
        {"id": incident_id, "org_id": user.org_id},
    ).mappings().first()
    if not inc:
        raise HTTPException(404, "Incidente nao encontrado")

    current = inc["status"]
    allowed = VALID_TRANSITIONS.get(current, [])
    if body.status not in allowed:
        raise HTTPException(400, f"Transicao invalida: {current} -> {body.status}")

    from app.core.query_builder import build_set_clause

    now = datetime.utcnow()
    update_parts = ["status = :status", "updated_at = :now"]
    params: dict = {"status": body.status, "now": now, "id": incident_id}

    if body.status == "mitigated":
        update_parts.append("mitigated_at = :now")
    elif body.status == "resolved":
        update_parts.append("resolved_at = :now")
        if body.resolution_summary:
            update_parts.append("resolution_summary = :summary")
            params["summary"] = body.resolution_summary

    set_clause = build_set_clause("incidents", update_parts)
    db.execute(
        text(f"UPDATE incidents SET {set_clause} WHERE id = :id"),
        params,
    )

    # Timeline event
    status_labels = {
        "investigating": "Em investigacao",
        "mitigated": "Mitigado",
        "resolved": "Resolvido",
    }
    db.execute(
        text("""
            INSERT INTO incident_timeline
                (id, incident_id, org_id, event_type, content, created_by)
            VALUES (:id, :incident_id, :org_id, :event_type, :content, :created_by)
        """),
        {
            "id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "org_id": user.org_id,
            "event_type": body.status,
            "content": f"Status alterado para {status_labels.get(body.status, body.status)} por {user.name}",
            "created_by": user.id,
        },
    )
    db.commit()

    # Background: generate post-mortem on resolve
    if body.status == "resolved":
        bg.add_task(_run_postmortem_generation, db, incident_id, user.org_id)

    bg.add_task(_notify_incident, db, incident_id, body.status)

    return {"id": incident_id, "status": body.status}


def _run_postmortem_generation(db: Session, incident_id: str, org_id: str):
    from app.core import postmortem_generator
    try:
        postmortem_generator.generate(db, incident_id, org_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Falha ao gerar post-mortem: %s", e)


@router.patch("/{incident_id}/hypotheses/{hypothesis_id}")
def update_hypothesis(
    incident_id: str,
    hypothesis_id: str,
    body: UpdateHypothesisRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Confirm or discard a hypothesis."""
    if body.status not in ("confirmed", "discarded"):
        raise HTTPException(400, "Status invalido para hipotese")

    result = db.execute(
        text("""
            UPDATE incident_hypotheses
            SET status = :status, confirmed_by = :user_id
            WHERE id = :id AND incident_id = :incident_id AND org_id = :org_id
        """),
        {
            "status": body.status,
            "user_id": user.id,
            "id": hypothesis_id,
            "incident_id": incident_id,
            "org_id": user.org_id,
        },
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Hipotese nao encontrada")

    if body.status == "confirmed":
        hyp = db.execute(
            text("SELECT hypothesis FROM incident_hypotheses WHERE id = :id"),
            {"id": hypothesis_id},
        ).mappings().first()
        db.execute(
            text("""
                INSERT INTO incident_timeline
                    (id, incident_id, org_id, event_type, content, created_by)
                VALUES (:id, :incident_id, :org_id, 'update', :content, :created_by)
            """),
            {
                "id": str(uuid.uuid4()),
                "incident_id": incident_id,
                "org_id": user.org_id,
                "content": f"Hipotese confirmada por {user.name}: {hyp['hypothesis'][:200] if hyp else ''}",
                "created_by": user.id,
            },
        )

    db.commit()
    return {"id": hypothesis_id, "status": body.status}


# ---------- Similar Incidents ----------


@router.get("/{incident_id}/similar")
def get_similar_incidents(
    incident_id: str,
    bg: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Get or compute similar resolved incidents."""
    inc = db.execute(
        text("SELECT id FROM incidents WHERE id = :id AND org_id = :org_id"),
        {"id": incident_id, "org_id": user.org_id},
    ).mappings().first()
    if not inc:
        raise HTTPException(404, "Incidente nao encontrado")

    # Check cached
    cached = db.execute(
        text("""
            SELECT si.similar_incident_id, si.similarity_score,
                   i.title, i.severity, i.resolved_at, i.resolution_summary,
                   mp.name as project_name
            FROM incident_similar_incidents si
            JOIN incidents i ON i.id = si.similar_incident_id
            JOIN monitored_projects mp ON mp.id = i.project_id
            WHERE si.incident_id = :id
            ORDER BY si.similarity_score DESC
            LIMIT 5
        """),
        {"id": incident_id},
    ).mappings().all()

    if cached:
        return {"similar": [dict(r) for r in cached]}

    # Trigger background search
    bg.add_task(_run_find_similar, db, incident_id, user.org_id)
    return {"similar": [], "computing": True}


def _run_find_similar(db: Session, incident_id: str, org_id: str):
    from app.core.incident_analyzer import IncidentAnalyzer
    try:
        analyzer = IncidentAnalyzer(db, org_id)
        analyzer.find_similar(incident_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Falha ao buscar incidentes similares: %s", e)


# ---------- Share Post-mortem ----------


@router.post("/{incident_id}/share")
def create_share_token(
    incident_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Generate a share token for public post-mortem access."""
    inc = db.execute(
        text("SELECT id, share_token, postmortem FROM incidents WHERE id = :id AND org_id = :org_id"),
        {"id": incident_id, "org_id": user.org_id},
    ).mappings().first()
    if not inc:
        raise HTTPException(404, "Incidente nao encontrado")
    if not inc["postmortem"]:
        raise HTTPException(400, "Post-mortem ainda nao foi gerado")

    # Return existing or generate new
    token = inc["share_token"]
    if not token:
        token = secrets.token_urlsafe(32)
        db.execute(
            text("UPDATE incidents SET share_token = :token WHERE id = :id"),
            {"token": token, "id": incident_id},
        )
        db.commit()

    from app.config import settings
    app_url = settings.app_url
    return {
        "share_token": token,
        "public_url": f"{app_url}/postmortem/{token}",
    }


@router.delete("/{incident_id}/share")
def revoke_share_token(
    incident_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Revoke the share token for a post-mortem."""
    result = db.execute(
        text("UPDATE incidents SET share_token = NULL WHERE id = :id AND org_id = :org_id"),
        {"id": incident_id, "org_id": user.org_id},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Incidente nao encontrado")
    db.commit()
    return {"status": "revoked"}


# ---------- Public Post-mortem router (separate, no prefix) ----------

public_router = APIRouter()


@public_router.get("/api/postmortem/{share_token}")
def get_public_postmortem(
    share_token: str,
    db: Session = Depends(get_session),
):
    """Public endpoint to view a shared post-mortem (no auth required)."""
    inc = db.execute(
        text("""
            SELECT i.title, i.severity, i.declared_at, i.resolved_at,
                   i.postmortem, i.postmortem_generated_at, mp.name as project_name
            FROM incidents i
            JOIN monitored_projects mp ON mp.id = i.project_id
            WHERE i.share_token = :token AND i.postmortem IS NOT NULL
        """),
        {"token": share_token},
    ).mappings().first()

    if not inc:
        raise HTTPException(404, "Post-mortem nao encontrado ou link expirado")

    return {
        "title": inc["title"],
        "severity": inc["severity"],
        "project_name": inc["project_name"],
        "declared_at": str(inc["declared_at"]) if inc["declared_at"] else None,
        "resolved_at": str(inc["resolved_at"]) if inc["resolved_at"] else None,
        "postmortem": inc["postmortem"],
        "postmortem_generated_at": str(inc["postmortem_generated_at"]) if inc["postmortem_generated_at"] else None,
    }


@router.get("/{incident_id}/postmortem/pdf")
def download_postmortem_pdf(
    incident_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Download post-mortem as PDF."""
    inc = db.execute(
        text("""
            SELECT i.*, mp.name as project_name, u.name as declared_by_name
            FROM incidents i
            JOIN monitored_projects mp ON mp.id = i.project_id
            LEFT JOIN users u ON u.id = i.declared_by
            WHERE i.id = :id AND i.org_id = :org_id
        """),
        {"id": incident_id, "org_id": user.org_id},
    ).mappings().first()

    if not inc:
        raise HTTPException(404, "Incidente nao encontrado")

    from app.core.pdf_generator import PDFGenerator

    pdf = PDFGenerator().generate_postmortem(dict(inc))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="postmortem-{incident_id}.pdf"'},
    )
