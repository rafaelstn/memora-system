"""Scheduler periodico para health check dos bancos Enterprise.

Executa a cada 30 minutos para todas as orgs Enterprise com setup completo.
Notifica admins por email em caso de transicao de status (ok->error ou error->ok).
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 30 * 60  # 30 minutos
_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _run_all_health_checks():
    """Executa health check em todas as orgs Enterprise."""
    from app.core.enterprise_db import check_health, get_all_enterprise_org_ids

    org_ids = get_all_enterprise_org_ids()
    if not org_ids:
        return

    logger.info(f"Enterprise health check: verificando {len(org_ids)} org(s)")

    for org_id in org_ids:
        try:
            result = check_health(org_id)
            prev = result.get("previous_status")
            curr = result["status"]

            if prev and prev != curr:
                _notify_transition(org_id, curr, result.get("error"))

            if curr == "error":
                logger.warning(f"Enterprise health FAIL para org {org_id}: {result.get('error')}")
        except Exception as e:
            logger.error(f"Enterprise health check error para org {org_id}: {e}")


def _notify_transition(org_id: str, new_status: str, error: str | None):
    """Envia email de notificacao na transicao de status."""
    try:
        from app.api.routes.enterprise import _notify_health_transition
        _notify_health_transition(org_id, new_status, error)
    except Exception as e:
        logger.error(f"Falha ao notificar transicao para org {org_id}: {e}")


def _scheduler_loop():
    """Loop principal do scheduler."""
    logger.info("Enterprise health scheduler iniciado (intervalo: 30min)")
    while not _stop_event.is_set():
        try:
            _run_all_health_checks()
        except Exception as e:
            logger.error(f"Enterprise health scheduler error: {e}")

        _stop_event.wait(_INTERVAL_SECONDS)

    logger.info("Enterprise health scheduler parado")


def start_scheduler():
    """Inicia o scheduler em background thread."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="enterprise-health")
    _scheduler_thread.start()


def stop_scheduler():
    """Para o scheduler."""
    _stop_event.set()
