"""Notificacoes proativas — verifica condicoes e dispara banners/emails."""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.email_client import send_to_org_admins

logger = logging.getLogger(__name__)

# ────────────── Constantes ──────────────

NOTIFICATION_TYPES = {
    "repo_outdated": "Repositorio desatualizado",
    "rules_changed": "Regras de negocio alteradas",
    "dev_inactive": "Dev novo inativo",
    "critical_alerts": "Alertas criticos acumulados",
}

COOLDOWN_DAYS = 7  # Don't resend same type within 7 days per org


# ────────────── Helpers ──────────────


def _was_recently_sent(
    db: Session,
    org_id: str,
    notification_type: str,
    days: int = COOLDOWN_DAYS,
) -> bool:
    """Verifica se uma notificacao do mesmo tipo ja foi enviada recentemente."""
    row = db.execute(
        text("""
            SELECT 1 FROM proactive_notifications_log
            WHERE org_id = :org_id
              AND notification_type = :ntype
              AND created_at > NOW() - MAKE_INTERVAL(days => :days)
            LIMIT 1
        """),
        {"org_id": org_id, "ntype": notification_type, "days": days},
    ).fetchone()
    return row is not None


def _log_notification(
    db: Session,
    org_id: str,
    notification_type: str,
    channel: str,
    detail: str | None = None,
) -> str:
    """Insere registro na tabela proactive_notifications_log. Retorna o id."""
    notif_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO proactive_notifications_log
                (id, org_id, notification_type, channel, detail, created_at)
            VALUES
                (:id, :org_id, :ntype, :channel, :detail, NOW())
        """),
        {
            "id": notif_id,
            "org_id": org_id,
            "ntype": notification_type,
            "channel": channel,
            "detail": detail,
        },
    )
    db.commit()
    return notif_id


# ────────────── Checks individuais ──────────────


def check_repo_outdated(
    db: Session,
    org_id: str,
    product_id: str,
) -> list[dict]:
    """Retorna repos cuja ultima ingestao tem mais de 7 dias."""
    rows = db.execute(
        text("""
            SELECT repo_name,
                   EXTRACT(DAY FROM NOW() - MAX(created_at))::int AS days_since
            FROM code_chunks
            WHERE org_id = :org_id
            GROUP BY repo_name
            HAVING MAX(created_at) < NOW() - INTERVAL '7 days'
            ORDER BY days_since DESC
        """),
        {"org_id": org_id},
    ).fetchall()

    return [
        {
            "repo_name": r.repo_name,
            "days_since": r.days_since,
            "product_id": product_id,
        }
        for r in rows
    ]


def check_rules_changed(
    db: Session,
    org_id: str,
    product_id: str,
) -> dict | None:
    """Verifica se 3+ regras de negocio foram alteradas nos ultimos 7 dias."""
    row = db.execute(
        text("""
            SELECT COUNT(*) AS cnt
            FROM knowledge_entries
            WHERE org_id = :org_id
              AND entry_type = 'business_rules'
              AND updated_at > NOW() - INTERVAL '7 days'
        """),
        {"org_id": org_id},
    ).fetchone()

    if row and row.cnt >= 3:
        return {"count": row.cnt, "product_id": product_id}
    return None


def check_dev_inactive(db: Session, org_id: str) -> list[dict]:
    """Encontra devs criados ha 3-7 dias sem nenhuma conversa."""
    rows = db.execute(
        text("""
            SELECT u.id AS user_id,
                   u.name,
                   EXTRACT(DAY FROM NOW() - u.created_at)::int AS days_since_join
            FROM users u
            LEFT JOIN conversations c ON c.user_id = u.id
            WHERE u.org_id = :org_id
              AND u.role = 'dev'
              AND u.created_at BETWEEN NOW() - INTERVAL '7 days'
                                    AND NOW() - INTERVAL '3 days'
            GROUP BY u.id, u.name, u.created_at
            HAVING COUNT(c.id) = 0
            ORDER BY days_since_join DESC
        """),
        {"org_id": org_id},
    ).fetchall()

    return [
        {
            "user_id": str(r.user_id),
            "name": r.name,
            "days_since_join": r.days_since_join,
        }
        for r in rows
    ]


def check_critical_alerts(
    db: Session,
    org_id: str,
    product_id: str,
) -> dict | None:
    """Conta alertas nao resolvidos criados ha mais de 48h."""
    row = db.execute(
        text("""
            SELECT COUNT(*) AS cnt
            FROM error_alerts ea
            JOIN monitored_projects mp ON mp.id = ea.project_id
            WHERE mp.org_id = :org_id
              AND ea.status != 'resolved'
              AND ea.created_at < NOW() - INTERVAL '48 hours'
        """),
        {"org_id": org_id},
    ).fetchone()

    if row and row.cnt >= 5:
        return {"count": row.cnt, "product_id": product_id}
    return None


# ────────────── Banners ──────────────


def get_active_banners(db: Session, org_id: str) -> list[dict]:
    """Retorna banners ativos (nao dispensados) para a organizacao."""
    rows = db.execute(
        text("""
            SELECT id, notification_type, detail, created_at
            FROM proactive_notifications_log
            WHERE org_id = :org_id
              AND channel = 'banner'
              AND resolved_at IS NULL
            ORDER BY created_at DESC
            LIMIT 10
        """),
        {"org_id": org_id},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "notification_type": r.notification_type,
            "title": NOTIFICATION_TYPES.get(r.notification_type, r.notification_type),
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def dismiss_banner(db: Session, notification_id: str, org_id: str) -> bool:
    """Dispensa um banner (marca resolved_at). Retorna True se encontrado."""
    result = db.execute(
        text("""
            UPDATE proactive_notifications_log
            SET resolved_at = NOW()
            WHERE id = :nid
              AND org_id = :org_id
              AND resolved_at IS NULL
        """),
        {"nid": notification_id, "org_id": org_id},
    )
    db.commit()
    return result.rowcount > 0


# ────────────── Orquestrador principal ──────────────


def check_and_notify(db: Session, org_id: str) -> list[str]:
    """Executa todas as verificacoes e dispara notificacoes.

    Retorna lista de tipos de notificacao disparados.
    """
    triggered: list[str] = []

    # Obter product_id padrao (primeiro projeto monitorado da org)
    proj = db.execute(
        text("""
            SELECT id FROM monitored_projects
            WHERE org_id = :org_id
            ORDER BY created_at ASC
            LIMIT 1
        """),
        {"org_id": org_id},
    ).fetchone()
    product_id = str(proj.id) if proj else ""

    # ── 1. Repositorios desatualizados ──
    ntype = "repo_outdated"
    if not _was_recently_sent(db, org_id, ntype):
        outdated = check_repo_outdated(db, org_id, product_id)
        if outdated:
            repos_txt = ", ".join(
                f"{r['repo_name']} ({r['days_since']}d)" for r in outdated
            )
            detail = f"Repositorios desatualizados: {repos_txt}"
            _log_notification(db, org_id, ntype, "banner", detail)

            try:
                send_to_org_admins(
                    db,
                    org_id,
                    subject=f"Memora — {NOTIFICATION_TYPES[ntype]}",
                    body_html=f"<p>{detail}</p><p>Considere re-indexar esses repositorios.</p>",
                )
                _log_notification(db, org_id, ntype, "email", detail)
            except Exception as e:
                logger.error("Falha ao enviar email (%s): %s", ntype, e)

            triggered.append(ntype)
            logger.info("Notificacao proativa [%s] para org %s", ntype, org_id)

    # ── 2. Regras de negocio alteradas ──
    ntype = "rules_changed"
    if not _was_recently_sent(db, org_id, ntype):
        result = check_rules_changed(db, org_id, product_id)
        if result:
            detail = (
                f"{result['count']} regras de negocio alteradas nos ultimos 7 dias"
            )
            _log_notification(db, org_id, ntype, "banner", detail)

            try:
                send_to_org_admins(
                    db,
                    org_id,
                    subject=f"Memora — {NOTIFICATION_TYPES[ntype]}",
                    body_html=(
                        f"<p>{detail}.</p>"
                        "<p>Revise as mudancas para garantir que a base de conhecimento esta atualizada.</p>"
                    ),
                )
                _log_notification(db, org_id, ntype, "email", detail)
            except Exception as e:
                logger.error("Falha ao enviar email (%s): %s", ntype, e)

            triggered.append(ntype)
            logger.info("Notificacao proativa [%s] para org %s", ntype, org_id)

    # ── 3. Devs inativos ──
    ntype = "dev_inactive"
    if not _was_recently_sent(db, org_id, ntype):
        inactive = check_dev_inactive(db, org_id)
        if inactive:
            names = ", ".join(f"{d['name']} ({d['days_since_join']}d)" for d in inactive)
            detail = f"Devs novos sem atividade: {names}"
            _log_notification(db, org_id, ntype, "banner", detail)

            try:
                send_to_org_admins(
                    db,
                    org_id,
                    subject=f"Memora — {NOTIFICATION_TYPES[ntype]}",
                    body_html=(
                        f"<p>{detail}.</p>"
                        "<p>Considere enviar um lembrete ou oferecer ajuda no onboarding.</p>"
                    ),
                )
                _log_notification(db, org_id, ntype, "email", detail)
            except Exception as e:
                logger.error("Falha ao enviar email (%s): %s", ntype, e)

            triggered.append(ntype)
            logger.info("Notificacao proativa [%s] para org %s", ntype, org_id)

    # ── 4. Alertas criticos acumulados ──
    ntype = "critical_alerts"
    if not _was_recently_sent(db, org_id, ntype):
        result = check_critical_alerts(db, org_id, product_id)
        if result:
            detail = (
                f"{result['count']} alertas nao resolvidos ha mais de 48 horas"
            )
            _log_notification(db, org_id, ntype, "banner", detail)

            try:
                send_to_org_admins(
                    db,
                    org_id,
                    subject=f"Memora — {NOTIFICATION_TYPES[ntype]}",
                    body_html=(
                        f"<p>{detail}.</p>"
                        "<p>Acesse o painel de monitoramento para revisar os alertas pendentes.</p>"
                    ),
                )
                _log_notification(db, org_id, ntype, "email", detail)
            except Exception as e:
                logger.error("Falha ao enviar email (%s): %s", ntype, e)

            triggered.append(ntype)
            logger.info("Notificacao proativa [%s] para org %s", ntype, org_id)

    return triggered
