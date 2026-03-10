"""Gerador de snapshots semanais para o painel executivo."""
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def generate_weekly_snapshot(
    db: Session,
    org_id: str,
    product_id: str,
    week_start: datetime,
    week_end: datetime,
) -> dict:
    """Calcula metricas da semana e retorna snapshot."""
    params = {
        "org_id": org_id,
        "product_id": product_id,
        "week_start": week_start,
        "week_end": week_end,
    }

    snapshot = {
        "security_score_avg": None,
        "error_alert_count": 0,
        "support_question_count": 0,
        "code_review_score_avg": None,
        "prs_reviewed_count": 0,
        "incident_resolution_avg_hours": None,
        "doc_coverage_pct": None,
    }

    # 1. Score de seguranca medio
    try:
        row = db.execute(
            text("""
                SELECT AVG(ss.overall_score) AS avg_score
                FROM security_scans ss
                WHERE ss.org_id = :org_id AND ss.product_id = :product_id
                  AND ss.status = 'completed'
                  AND ss.created_at >= :week_start AND ss.created_at < :week_end
            """), params,
        ).mappings().first()
        if row and row["avg_score"] is not None:
            snapshot["security_score_avg"] = round(float(row["avg_score"]), 1)
    except Exception as e:
        logger.warning("Snapshot: erro security_score: %s", e)

    # 2. Frequencia de erros
    try:
        val = db.execute(
            text("""
                SELECT COUNT(*) AS cnt FROM error_alerts ea
                JOIN monitored_projects mp ON mp.id = ea.project_id
                WHERE mp.org_id = :org_id
                  AND ea.created_at >= :week_start AND ea.created_at < :week_end
            """), params,
        ).scalar() or 0
        snapshot["error_alert_count"] = val
    except Exception as e:
        logger.warning("Snapshot: erro error_alerts: %s", e)

    # 3. Volume de perguntas suporte
    try:
        val = db.execute(
            text("""
                SELECT COUNT(*) AS cnt FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.org_id = :org_id AND c.product_id = :product_id
                  AND m.role = 'user'
                  AND m.created_at >= :week_start AND m.created_at < :week_end
            """), params,
        ).scalar() or 0
        snapshot["support_question_count"] = val
    except Exception as e:
        logger.warning("Snapshot: erro support_questions: %s", e)

    # 4. Score medio de code review
    try:
        row = db.execute(
            text("""
                SELECT AVG(overall_score) AS avg_score, COUNT(*) AS cnt
                FROM code_reviews
                WHERE org_id = :org_id AND product_id = :product_id
                  AND created_at >= :week_start AND created_at < :week_end
            """), params,
        ).mappings().first()
        if row:
            if row["avg_score"] is not None:
                snapshot["code_review_score_avg"] = round(float(row["avg_score"]), 1)
            snapshot["prs_reviewed_count"] = row["cnt"] or 0
    except Exception as e:
        logger.warning("Snapshot: erro code_reviews: %s", e)

    # 5. Tempo medio resolucao incidentes
    try:
        val = db.execute(
            text("""
                SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600) AS avg_h
                FROM incidents
                WHERE org_id = :org_id
                  AND status = 'resolved'
                  AND resolved_at >= :week_start AND resolved_at < :week_end
            """), params,
        ).scalar()
        if val is not None:
            snapshot["incident_resolution_avg_hours"] = round(float(val), 1)
    except Exception as e:
        logger.warning("Snapshot: erro incidents: %s", e)

    # 6. Cobertura de documentacao
    try:
        total_repos = db.execute(
            text("""
                SELECT COUNT(DISTINCT repo_name) AS cnt FROM code_chunks
                WHERE org_id = :org_id AND product_id = :product_id
            """), params,
        ).scalar() or 0

        documented = db.execute(
            text("""
                SELECT COUNT(DISTINCT repo_name) AS cnt FROM repo_docs
                WHERE org_id = :org_id
            """), {"org_id": org_id},
        ).scalar() or 0

        if total_repos > 0:
            snapshot["doc_coverage_pct"] = round(documented / total_repos * 100, 1)
    except Exception as e:
        logger.warning("Snapshot: erro doc_coverage: %s", e)

    return snapshot


def save_weekly_snapshot(
    db: Session,
    org_id: str,
    product_id: str,
    week_start: datetime | None = None,
    week_end: datetime | None = None,
) -> dict:
    """Gera e salva snapshot semanal. Retorna o snapshot completo."""
    if week_start is None or week_end is None:
        today = datetime.utcnow().date()
        week_end_date = today - timedelta(days=today.weekday())
        week_start_date = week_end_date - timedelta(days=7)
        week_start = datetime.combine(week_start_date, datetime.min.time())
        week_end = datetime.combine(week_end_date, datetime.min.time())

    snapshot = generate_weekly_snapshot(db, org_id, product_id, week_start, week_end)
    snap_id = str(uuid.uuid4())

    try:
        db.execute(
            text("""
                INSERT INTO executive_weekly_snapshots
                    (id, org_id, product_id, week_start, week_end,
                     security_score_avg, error_alert_count, support_question_count,
                     code_review_score_avg, prs_reviewed_count,
                     incident_resolution_avg_hours, doc_coverage_pct)
                VALUES
                    (:id, :org_id, :product_id, :week_start, :week_end,
                     :security_score_avg, :error_alert_count, :support_question_count,
                     :code_review_score_avg, :prs_reviewed_count,
                     :incident_resolution_avg_hours, :doc_coverage_pct)
            """),
            {
                "id": snap_id,
                "org_id": org_id,
                "product_id": product_id,
                "week_start": week_start,
                "week_end": week_end,
                **snapshot,
            },
        )
        db.commit()
    except Exception as e:
        logger.error("Falha ao salvar snapshot semanal: %s", e)
        try:
            db.rollback()
        except Exception:
            pass

    return {"id": snap_id, "org_id": org_id, "product_id": product_id, **snapshot}


def get_history(
    db: Session,
    org_id: str,
    product_id: str,
    period: str = "4w",
) -> list[dict]:
    """Retorna snapshots historicos filtrados por periodo."""
    weeks_map = {"4w": 4, "3m": 13, "6m": 26}
    weeks = weeks_map.get(period, 4)

    rows = db.execute(
        text("""
            SELECT * FROM executive_weekly_snapshots
            WHERE org_id = :org_id AND product_id = :product_id
              AND week_start >= NOW() - MAKE_INTERVAL(weeks => :weeks)
            ORDER BY week_start ASC
        """),
        {"org_id": org_id, "product_id": product_id, "weeks": weeks},
    ).mappings().all()

    return [dict(r) for r in rows]


def get_history_csv(
    db: Session,
    org_id: str,
    product_id: str,
    period: str = "4w",
) -> str:
    """Retorna CSV dos snapshots."""
    rows = get_history(db, org_id, product_id, period)

    headers = [
        "week_start", "week_end", "security_score_avg", "error_alert_count",
        "support_question_count", "code_review_score_avg", "prs_reviewed_count",
        "incident_resolution_avg_hours", "doc_coverage_pct",
    ]

    lines = [",".join(headers)]
    for r in rows:
        values = []
        for h in headers:
            v = r.get(h)
            values.append(str(v) if v is not None else "")
        lines.append(",".join(values))

    return "\n".join(lines)
