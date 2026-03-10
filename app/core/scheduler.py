"""Scheduler centralizado para jobs periodicos (digest semanal, notificacoes proativas)."""
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

_scheduler_thread = None
_stop_event = threading.Event()

# Schedule config (hora local Sao Paulo = UTC-3)
DIGEST_HOUR_UTC = 11  # 08h BRT = 11h UTC
DIGEST_WEEKDAY = 0    # Monday
PROACTIVE_HOUR_UTC = 12  # 09h BRT = 12h UTC
SNAPSHOT_HOUR_UTC = 3  # 00h BRT = 03h UTC (domingo 23:55 BRT ~ segunda 02:55 UTC)
SNAPSHOT_WEEKDAY = 0   # Monday (runs early Monday = captures Sunday night BRT)
CLEANUP_HOUR_UTC = 5   # 02h BRT = 05h UTC


def _should_run_digest(now: datetime) -> bool:
    return now.weekday() == DIGEST_WEEKDAY and now.hour == DIGEST_HOUR_UTC and now.minute < 5


def _should_run_proactive(now: datetime) -> bool:
    return now.hour == PROACTIVE_HOUR_UTC and now.minute < 5


def _should_run_snapshot(now: datetime) -> bool:
    return now.weekday() == SNAPSHOT_WEEKDAY and now.hour == SNAPSHOT_HOUR_UTC and now.minute < 5


def _should_run_cleanup(now: datetime) -> bool:
    return now.hour == CLEANUP_HOUR_UTC and now.minute < 5


def _run_digest_for_all_orgs():
    try:
        from app.db.session import SessionLocal
        from app.models.organization import Organization
        db = SessionLocal()
        try:
            orgs = db.query(Organization).filter(Organization.is_active.isnot(False)).all()
            for org in orgs:
                try:
                    from app.core.digest_generator import send_weekly_digest
                    send_weekly_digest(db, org.id)
                except Exception as e:
                    logger.warning(f"Digest falhou para org {org.id}: {e}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao executar digest semanal: {e}")


def _run_proactive_for_all_orgs():
    try:
        from app.db.session import SessionLocal
        from app.models.organization import Organization
        db = SessionLocal()
        try:
            orgs = db.query(Organization).filter(Organization.is_active.isnot(False)).all()
            for org in orgs:
                try:
                    from app.core.proactive_notifier import check_and_notify
                    check_and_notify(db, org.id)
                except Exception as e:
                    logger.warning(f"Proactive check falhou para org {org.id}: {e}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao executar checks proativos: {e}")


def _run_snapshots_for_all_orgs():
    try:
        from app.db.session import SessionLocal
        from app.models.organization import Organization
        from sqlalchemy import text as sql_text
        db = SessionLocal()
        try:
            orgs = db.query(Organization).filter(Organization.is_active.isnot(False)).all()
            for org in orgs:
                try:
                    products = db.execute(
                        sql_text("SELECT id FROM products WHERE org_id = :oid AND is_active = true"),
                        {"oid": org.id},
                    ).fetchall()
                    from app.core.executive_weekly import save_weekly_snapshot
                    for p in products:
                        save_weekly_snapshot(db, org.id, str(p.id))
                except Exception as e:
                    logger.warning(f"Snapshot falhou para org {org.id}: {e}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao executar snapshots semanais: {e}")


def _scheduler_loop():
    logger.info("Scheduler iniciado (digest segunda 08h BRT, proactive diario 09h BRT, snapshots segunda 00h BRT)")
    last_digest_date = None
    last_proactive_date = None
    last_snapshot_date = None
    last_cleanup_date = None

    while not _stop_event.is_set():
        try:
            now = datetime.utcnow()
            today = now.date()

            if _should_run_snapshot(now) and last_snapshot_date != today:
                last_snapshot_date = today
                logger.info("Executando snapshots semanais...")
                _run_snapshots_for_all_orgs()

            if _should_run_digest(now) and last_digest_date != today:
                last_digest_date = today
                logger.info("Executando digest semanal...")
                _run_digest_for_all_orgs()

            if _should_run_proactive(now) and last_proactive_date != today:
                last_proactive_date = today
                logger.info("Executando checks proativos...")
                _run_proactive_for_all_orgs()

            if _should_run_cleanup(now) and last_cleanup_date != today:
                last_cleanup_date = today
                try:
                    from app.db.session import SessionLocal as _SL
                    from app.core.data_exporter import cleanup_expired_exports
                    _db = _SL()
                    try:
                        removed = cleanup_expired_exports(_db)
                        if removed:
                            logger.info("Limpeza: %d exportacoes expiradas removidas", removed)
                    finally:
                        _db.close()
                except Exception as e:
                    logger.warning(f"Limpeza de exports falhou: {e}")

        except Exception as e:
            logger.error(f"Erro no scheduler loop: {e}")

        _stop_event.wait(60)  # Check every minute


def start_scheduler():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="memora-scheduler")
    _scheduler_thread.start()


def stop_scheduler():
    _stop_event.set()
    if _scheduler_thread:
        _scheduler_thread.join(timeout=5)
