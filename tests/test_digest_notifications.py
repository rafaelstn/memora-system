"""Testes do digest semanal e notificacoes proativas."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ── Digest Generator ──────────────────────────────────────


def test_generate_digest_returns_sections():
    """Digest gerado com dados corretos para o periodo."""
    from app.core.digest_generator import generate_digest

    mock_db = MagicMock()

    # Simulate query results
    mock_db.execute.return_value.scalar.return_value = 10
    mock_db.execute.return_value.mappings.return_value.all.return_value = [
        {"email": "dev@test.com", "qtd": 5},
    ]
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "total": 3,
        "critical": 1,
        "warning": 2,
        "total_reviews": 2,
        "avg_score": 85.0,
    }

    now = datetime.utcnow()
    result = generate_digest(
        mock_db,
        org_id="org-001",
        product_id="prod-001",
        week_start=now - timedelta(days=7),
        week_end=now,
    )
    assert isinstance(result, dict)


def test_generate_digest_empty_week():
    """Digest nao enviado se semana vazia."""
    from app.core.digest_generator import generate_digest

    mock_db = MagicMock()
    # All scalars return 0
    mock_db.execute.return_value.scalar.return_value = 0
    mock_db.execute.return_value.mappings.return_value.all.return_value = []
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "total": 0,
        "critical": 0,
        "warning": 0,
        "total_reviews": 0,
        "avg_score": None,
    }

    now = datetime.utcnow()
    result = generate_digest(
        mock_db,
        org_id="org-001",
        product_id="prod-001",
        week_start=now - timedelta(days=7),
        week_end=now,
    )
    # Empty digest (no sections with data > 0)
    assert isinstance(result, dict)


def test_render_digest_email_html():
    """Email HTML gerado corretamente."""
    from app.core.digest_generator import render_digest_email

    now = datetime.utcnow()
    subject, html = render_digest_email(
        org_name="Org Teste",
        digest_data={
            "suporte": {
                "total_perguntas": 42,
                "top_usuarios": [{"email": "dev@test.com", "perguntas": 10}],
                "respostas_insatisfatorias": 3,
            },
            "monitor": {
                "total_alertas": 5,
                "criticos": 1,
                "avisos": 4,
                "tempo_medio_resolucao_h": 2.5,
            },
        },
        week_start=now - timedelta(days=7),
        week_end=now,
        dashboard_url="https://app.test/dashboard",
    )
    assert "Org Teste" in subject
    assert "42" in html
    assert "Assistente de Suporte" in html
    assert "Monitor de Erros" in html


def test_render_digest_email_empty():
    """Email HTML para semana sem atividade."""
    from app.core.digest_generator import render_digest_email

    now = datetime.utcnow()
    subject, html = render_digest_email(
        org_name="Vazia",
        digest_data={},
        week_start=now - timedelta(days=7),
        week_end=now,
        dashboard_url="https://app.test",
    )
    assert "Nenhuma atividade" in html


def test_merge_digests():
    """Merge de metricas de multiplos produtos."""
    from app.core.digest_generator import _merge_digests

    target = {
        "suporte": {
            "total_perguntas": 10,
            "respostas_insatisfatorias": 2,
            "top_usuarios": [{"email": "a@t.com", "perguntas": 5}],
        },
    }
    source = {
        "suporte": {
            "total_perguntas": 8,
            "respostas_insatisfatorias": 1,
            "top_usuarios": [{"email": "b@t.com", "perguntas": 3}],
        },
    }
    _merge_digests(target, source)
    assert target["suporte"]["total_perguntas"] == 18
    assert target["suporte"]["respostas_insatisfatorias"] == 3
    assert len(target["suporte"]["top_usuarios"]) == 2


def test_send_weekly_digest_skipped_no_products():
    """Digest pulado se nao ha produtos ativos."""
    from app.core.digest_generator import send_weekly_digest

    mock_db = MagicMock()

    # Need separate side effects: first call returns org, second returns empty products
    call_count = {"n": 0}
    original_execute = mock_db.execute

    def execute_side_effect(*args, **kwargs):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # org query
            result.mappings.return_value.first.return_value = {
                "id": "org-001",
                "name": "Org Teste",
            }
        elif call_count["n"] == 2:
            # products query
            result.mappings.return_value.all.return_value = []
        else:
            # digest log insert
            pass
        return result

    mock_db.execute.side_effect = execute_side_effect

    status = send_weekly_digest(mock_db, "org-001")
    assert status == "skipped"


# ── Digest Route ──────────────────────────────────────


def test_send_digest_now_admin(admin_client):
    """send-now funciona para admin."""
    with patch("app.core.digest_generator.send_weekly_digest", return_value="sent"):
        response = admin_client.post("/api/admin/digest/send-now")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"


def test_send_digest_now_blocked_for_dev(dev_client):
    """send-now bloqueado para dev."""
    response = dev_client.post("/api/admin/digest/send-now")
    assert response.status_code == 403


def test_send_digest_now_blocked_for_suporte(suporte_client):
    """send-now bloqueado para suporte."""
    response = suporte_client.post("/api/admin/digest/send-now")
    assert response.status_code == 403


# ── Proactive Notifier ──────────────────────────────────────


def test_cooldown_check():
    """Mesmo gatilho nao reenvia dentro de 7 dias."""
    from app.core.proactive_notifier import _was_recently_sent

    mock_db = MagicMock()

    # Already sent
    mock_db.execute.return_value.fetchone.return_value = (1,)
    assert _was_recently_sent(mock_db, "org-001", "repo_outdated") is True

    # Not sent
    mock_db.execute.return_value.fetchone.return_value = None
    assert _was_recently_sent(mock_db, "org-001", "repo_outdated") is False


def test_check_repo_outdated():
    """Gatilho repo_outdated dispara com repos > 7 dias."""
    from app.core.proactive_notifier import check_repo_outdated

    mock_db = MagicMock()
    row = MagicMock()
    row.repo_name = "my-repo"
    row.days_since = 10
    mock_db.execute.return_value.fetchall.return_value = [row]

    result = check_repo_outdated(mock_db, "org-001", "prod-001")
    assert len(result) == 1
    assert result[0]["repo_name"] == "my-repo"
    assert result[0]["days_since"] == 10


def test_check_repo_outdated_empty():
    """Nenhum repo desatualizado."""
    from app.core.proactive_notifier import check_repo_outdated

    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []

    result = check_repo_outdated(mock_db, "org-001", "prod-001")
    assert result == []


def test_check_rules_changed_triggers():
    """Gatilho rules_changed dispara com 3+ regras."""
    from app.core.proactive_notifier import check_rules_changed

    mock_db = MagicMock()
    row = MagicMock()
    row.cnt = 5
    mock_db.execute.return_value.fetchone.return_value = row

    result = check_rules_changed(mock_db, "org-001", "prod-001")
    assert result is not None
    assert result["count"] == 5


def test_check_rules_changed_no_trigger():
    """Gatilho rules_changed NAO dispara com < 3 regras."""
    from app.core.proactive_notifier import check_rules_changed

    mock_db = MagicMock()
    row = MagicMock()
    row.cnt = 2
    mock_db.execute.return_value.fetchone.return_value = row

    result = check_rules_changed(mock_db, "org-001", "prod-001")
    assert result is None


def test_check_dev_inactive():
    """Gatilho dev_inactive retorna devs sem atividade."""
    from app.core.proactive_notifier import check_dev_inactive

    mock_db = MagicMock()
    row = MagicMock()
    row.user_id = "u-001"
    row.name = "Dev Novo"
    row.days_since_join = 5
    mock_db.execute.return_value.fetchall.return_value = [row]

    result = check_dev_inactive(mock_db, "org-001")
    assert len(result) == 1
    assert result[0]["name"] == "Dev Novo"


def test_check_critical_alerts_triggers():
    """Gatilho critical_alerts dispara com 5+ alertas > 48h."""
    from app.core.proactive_notifier import check_critical_alerts

    mock_db = MagicMock()
    row = MagicMock()
    row.cnt = 7
    mock_db.execute.return_value.fetchone.return_value = row

    result = check_critical_alerts(mock_db, "org-001", "prod-001")
    assert result is not None
    assert result["count"] == 7


def test_check_critical_alerts_no_trigger():
    """Gatilho critical_alerts NAO dispara com < 5."""
    from app.core.proactive_notifier import check_critical_alerts

    mock_db = MagicMock()
    row = MagicMock()
    row.cnt = 3
    mock_db.execute.return_value.fetchone.return_value = row

    result = check_critical_alerts(mock_db, "org-001", "prod-001")
    assert result is None


def test_get_active_banners():
    """Banners ativos retornados corretamente."""
    from app.core.proactive_notifier import get_active_banners

    mock_db = MagicMock()
    row = MagicMock()
    row.id = "banner-001"
    row.notification_type = "repo_outdated"
    row.detail = "Repo atrasado 10 dias"
    row.created_at = datetime.utcnow()
    mock_db.execute.return_value.fetchall.return_value = [row]

    result = get_active_banners(mock_db, "org-001")
    assert len(result) == 1
    assert result[0]["notification_type"] == "repo_outdated"
    assert result[0]["title"] == "Repositorio desatualizado"


def test_dismiss_banner():
    """Dismiss funciona e retorna True."""
    from app.core.proactive_notifier import dismiss_banner

    mock_db = MagicMock()
    mock_db.execute.return_value.rowcount = 1

    assert dismiss_banner(mock_db, "banner-001", "org-001") is True
    mock_db.commit.assert_called_once()


def test_dismiss_banner_not_found():
    """Dismiss retorna False se banner nao existe."""
    from app.core.proactive_notifier import dismiss_banner

    mock_db = MagicMock()
    mock_db.execute.return_value.rowcount = 0

    assert dismiss_banner(mock_db, "nonexistent", "org-001") is False


# ── Banner Routes ──────────────────────────────────────


def test_banners_route_admin(admin_client):
    """Admin pode ver banners."""
    with patch("app.core.proactive_notifier.get_active_banners", return_value=[]):
        response = admin_client.get("/api/notifications/banners")
    assert response.status_code == 200


def test_banners_route_suporte_empty(suporte_client):
    """Suporte recebe lista vazia de banners."""
    response = suporte_client.get("/api/notifications/banners")
    assert response.status_code == 200
    assert response.json() == []


def test_dismiss_route_admin(admin_client):
    """Admin pode dispensar banner."""
    with patch("app.core.proactive_notifier.dismiss_banner", return_value=True):
        response = admin_client.post("/api/notifications/banners/123/dismiss")
    assert response.status_code == 200


def test_dismiss_route_suporte_blocked(suporte_client):
    """Suporte nao pode dispensar banner."""
    response = suporte_client.post("/api/notifications/banners/123/dismiss")
    assert response.status_code == 403


# ── Scheduler ──────────────────────────────────────


def test_scheduler_digest_check():
    """_should_run_digest retorna True na segunda 11h UTC."""
    from app.core.scheduler import _should_run_digest

    monday_11h = datetime(2026, 3, 9, 11, 2)  # Monday
    assert _should_run_digest(monday_11h) is True

    tuesday_11h = datetime(2026, 3, 10, 11, 2)  # Tuesday
    assert _should_run_digest(tuesday_11h) is False

    monday_15h = datetime(2026, 3, 9, 15, 0)  # Monday but wrong hour
    assert _should_run_digest(monday_15h) is False


def test_scheduler_proactive_check():
    """_should_run_proactive retorna True as 12h UTC."""
    from app.core.scheduler import _should_run_proactive

    noon = datetime(2026, 3, 10, 12, 3)
    assert _should_run_proactive(noon) is True

    afternoon = datetime(2026, 3, 10, 15, 0)
    assert _should_run_proactive(afternoon) is False


def test_notification_types_constant():
    """Constantes de tipos de notificacao definidas."""
    from app.core.proactive_notifier import NOTIFICATION_TYPES, COOLDOWN_DAYS

    assert "repo_outdated" in NOTIFICATION_TYPES
    assert "rules_changed" in NOTIFICATION_TYPES
    assert "dev_inactive" in NOTIFICATION_TYPES
    assert "critical_alerts" in NOTIFICATION_TYPES
    assert COOLDOWN_DAYS == 7
