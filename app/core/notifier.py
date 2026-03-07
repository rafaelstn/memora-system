"""Sistema de notificacoes: email para admins + webhooks."""
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core import email_client

logger = logging.getLogger(__name__)


def _send_webhook(url: str, payload: dict) -> bool:
    """Send webhook POST. Returns True on success."""
    try:
        resp = httpx.post(url, json=payload, timeout=10)
        logger.info("Webhook %s retornou %d", url[:50], resp.status_code)
        return 200 <= resp.status_code < 300
    except Exception as e:
        logger.error("Falha no webhook %s: %s", url[:50], e)
        return False


def notify_alert(db: Session, alert_id: str):
    """Dispatch notifications for an alert: emails to admins + active webhooks."""
    alert = db.execute(
        text("""
            SELECT ea.*, mp.name as project_name
            FROM error_alerts ea
            JOIN monitored_projects mp ON mp.id = ea.project_id
            WHERE ea.id = :id
        """),
        {"id": alert_id},
    ).mappings().first()

    if not alert:
        logger.warning("Alerta %s nao encontrado para notificacao", alert_id)
        return

    org_id = alert["org_id"]
    app_url = settings.app_url
    detail_url = f"{app_url}/dashboard/monitor/{alert['project_id']}"

    # Build email with template
    subject, body_html = email_client.build_alert_email(
        dict(alert), alert["project_name"], detail_url
    )

    # Send emails to org admins
    email_client.send_to_org_admins(db, org_id, subject, body_html, "alert")

    # Send webhooks
    suggested = alert.get("suggested_actions") or []
    if isinstance(suggested, str):
        import json
        try:
            suggested = json.loads(suggested)
        except Exception:
            suggested = [suggested]

    webhook_payload = {
        "alert_id": alert["id"],
        "project": alert["project_name"],
        "title": alert["title"],
        "severity": alert["severity"],
        "explanation": alert["explanation"],
        "affected_component": alert.get("affected_component"),
        "suggested_actions": suggested,
        "occurred_at": str(alert["created_at"]) if alert.get("created_at") else None,
        "url": detail_url,
    }

    webhooks = db.execute(
        text("SELECT url FROM alert_webhooks WHERE org_id = :org_id AND is_active = true"),
        {"org_id": org_id},
    ).mappings().all()

    for wh in webhooks:
        _send_webhook(wh["url"], webhook_payload)

    # Mark notification as sent
    db.execute(
        text("UPDATE error_alerts SET notification_sent = true WHERE id = :id"),
        {"id": alert_id},
    )
    db.commit()

    logger.info("Notificacoes enviadas para alerta %s", alert_id)


def notify_incident_declared(db: Session, incident: dict):
    """Notify admins when incident is declared."""
    app_url = settings.app_url
    detail_url = f"{app_url}/dashboard/monitor/incidents/{incident['id']}"
    subject, body_html = email_client.build_incident_declared_email(incident, detail_url)
    email_client.send_to_org_admins(db, incident["org_id"], subject, body_html, "incident")


def notify_incident_resolved(db: Session, incident: dict):
    """Notify admins when incident is resolved."""
    app_url = settings.app_url
    detail_url = f"{app_url}/dashboard/monitor/incidents/{incident['id']}"
    subject, body_html = email_client.build_incident_resolved_email(incident, detail_url)
    email_client.send_to_org_admins(db, incident["org_id"], subject, body_html, "incident")


def notify_incident_no_update(db: Session, incident: dict):
    """Remind admins about stale incidents."""
    app_url = settings.app_url
    detail_url = f"{app_url}/dashboard/monitor/incidents/{incident['id']}"
    subject, body_html = email_client.build_incident_no_update_email(incident, detail_url)
    email_client.send_to_org_admins(db, incident["org_id"], subject, body_html, "incident")


def test_webhook(url: str) -> dict:
    """Send a test payload to a webhook URL."""
    payload = {
        "alert_id": "test-000",
        "project": "Projeto de Teste",
        "title": "Teste de webhook — Memora",
        "severity": "low",
        "explanation": "Este e um teste de webhook do Memora.",
        "suggested_actions": ["Nenhuma acao necessaria"],
        "url": "https://memora.app/test",
    }
    try:
        resp = httpx.post(url, json=payload, timeout=10)
        return {"status": "ok", "http_status": resp.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)[:500]}
