"""Detecta incidentes stale (sem atualizacao) e envia lembretes."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import email_client

logger = logging.getLogger(__name__)

STALE_THRESHOLD_MINUTES = 60


def check_stale_incidents(db: Session):
    """Find active incidents without updates for > 1h and send reminder emails."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_THRESHOLD_MINUTES)

    stale = db.execute(
        text("""
            SELECT i.id, i.org_id, i.title, i.status, i.project_id,
                   mp.name as project_name,
                   (SELECT MAX(t.created_at)
                    FROM incident_timeline t
                    WHERE t.incident_id = i.id) as last_update
            FROM incidents i
            JOIN monitored_projects mp ON mp.id = i.project_id
            WHERE i.status IN ('open', 'investigating', 'mitigated')
              AND (
                  (SELECT MAX(t.created_at)
                   FROM incident_timeline t
                   WHERE t.incident_id = i.id) < :cutoff
                  OR NOT EXISTS (
                      SELECT 1 FROM incident_timeline t
                      WHERE t.incident_id = i.id
                        AND t.created_at >= :cutoff
                  )
              )
        """),
        {"cutoff": cutoff},
    ).mappings().all()

    sent = 0
    for inc in stale:
        from app.config import settings
        app_url = settings.app_url
        detail_url = f"{app_url}/dashboard/monitor/incidents/{inc['id']}"

        subject, body = email_client.build_incident_no_update_email(
            dict(inc), detail_url,
        )
        count = email_client.send_to_org_admins(
            db, inc["org_id"], subject, body, "incident",
        )
        if count > 0:
            sent += 1
            logger.info("Lembrete enviado para incidente stale %s", inc["id"])

    if sent:
        logger.info("Watchdog: %d lembretes enviados para incidentes stale", sent)
    return sent
