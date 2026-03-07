"""Tests for email client, templates, and notification preferences."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_session
from app.main import app
from tests.conftest import _fake_user


# ────────────── Fixtures ──────────────


def _mock_session() -> MagicMock:
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session


@pytest.fixture()
def admin_client():
    fake = _fake_user("admin")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def dev_client():
    fake = _fake_user("dev")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def suporte_client():
    fake = _fake_user("suporte")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# ────────────── Template Builder Tests ──────────────


class TestTemplateBuilders:
    """Test that each template builder produces valid HTML with expected content."""

    def test_build_alert_email(self):
        from app.core.email_client import build_alert_email

        alert = {
            "title": "NullPointerException",
            "severity": "high",
            "explanation": "Erro no servico de pagamento",
            "affected_component": "payment-service",
            "suggested_actions": ["Verificar logs", "Reiniciar servico"],
        }
        subject, body = build_alert_email(alert, "meu-projeto", "https://app.com/alert/1")
        assert "[HIGH]" in subject
        assert "NullPointerException" in subject
        assert "meu-projeto" in subject
        assert "NullPointerException" in body
        assert "payment-service" in body
        assert "Verificar logs" in body
        assert "Ver no Memora" in body

    def test_build_alert_email_string_actions(self):
        from app.core.email_client import build_alert_email

        alert = {
            "title": "Timeout",
            "severity": "critical",
            "suggested_actions": '["Acao 1", "Acao 2"]',
        }
        subject, body = build_alert_email(alert, "proj", "https://x.com/1")
        assert "[CRITICAL]" in subject
        assert "Acao 1" in body

    def test_build_incident_declared_email(self):
        from app.core.email_client import build_incident_declared_email

        incident = {
            "title": "API fora do ar",
            "severity": "critical",
            "project_name": "api-prod",
            "declared_by_name": "Rafael",
            "description": "Timeout em todos os endpoints",
        }
        subject, body = build_incident_declared_email(incident, "https://app.com/incident/1")
        assert "Incidente declarado" in subject
        assert "API fora do ar" in body
        assert "Rafael" in body
        assert "Abrir War Room" in body

    def test_build_incident_resolved_email(self):
        from app.core.email_client import build_incident_resolved_email

        incident = {
            "title": "API fora do ar",
            "project_name": "api-prod",
            "resolution_summary": "Corrigido timeout no DB pool",
        }
        subject, body = build_incident_resolved_email(incident, "https://app.com/incident/1")
        assert "resolvido" in subject.lower()
        assert "Corrigido timeout" in body
        assert "Ver Post-mortem" in body

    def test_build_incident_no_update_email(self):
        from app.core.email_client import build_incident_no_update_email

        incident = {
            "title": "Lentidao no checkout",
            "status": "investigating",
            "project_name": "ecommerce",
        }
        subject, body = build_incident_no_update_email(incident, "https://app.com/incident/2")
        assert "Sem atualizacao" in subject
        assert "Lentidao no checkout" in body
        assert "Atualizar War Room" in body

    def test_build_security_scan_email(self):
        from app.core.email_client import build_security_scan_email

        scan = {
            "repo_name": "memora-api",
            "security_score": 85,
            "critical_count": 0,
            "high_count": 1,
            "medium_count": 3,
        }
        subject, body = build_security_scan_email(scan, "https://app.com/scan/1")
        assert "85/100" in subject
        assert "memora-api" in body
        assert "Ver Detalhes" in body

    def test_build_security_scan_email_low_score(self):
        from app.core.email_client import build_security_scan_email

        scan = {"repo_name": "vuln-app", "security_score": 40}
        subject, _ = build_security_scan_email(scan, "https://x.com")
        assert "🔴" in subject

    def test_build_dast_scan_email(self):
        from app.core.email_client import build_dast_scan_email

        scan = {
            "target_url": "https://api.example.com",
            "vulnerabilities_confirmed": 2,
            "risk_level": "high",
            "summary": "SQL injection e XSS detectados",
        }
        subject, body = build_dast_scan_email(scan, "https://app.com/dast/1")
        assert "2 vulnerabilidades" in subject
        assert "SQL injection" in body
        assert "Ver Resultado" in body

    def test_build_dast_scan_email_no_vulns(self):
        from app.core.email_client import build_dast_scan_email

        scan = {"target_url": "https://safe.com", "vulnerabilities_confirmed": 0, "risk_level": "low"}
        subject, _ = build_dast_scan_email(scan, "https://x.com")
        assert "✅" in subject

    def test_build_review_email(self):
        from app.core.email_client import build_review_email

        review = {
            "id": "abcd1234-5678",
            "pr_title": "feat: add auth",
            "overall_score": 92,
            "overall_verdict": "approved",
            "summary": "Codigo limpo, bem estruturado",
        }
        subject, body = build_review_email(review, "https://app.com/review/1")
        assert "92/100" in subject
        assert "✅" in subject
        assert "feat: add auth" in body
        assert "Ver Review" in body

    def test_build_review_email_changes_requested(self):
        from app.core.email_client import build_review_email

        review = {"id": "abcd1234", "overall_score": 45, "overall_verdict": "changes_requested"}
        subject, _ = build_review_email(review, "https://x.com")
        assert "⚠️" in subject

    def test_build_executive_snapshot_email(self):
        from app.core.email_client import build_executive_snapshot_email

        snapshot = {
            "health_score": 75,
            "summary": "Sistema operacional com alertas moderados",
        }
        subject, body = build_executive_snapshot_email(snapshot, "https://app.com/executive")
        assert "75/100" in subject
        assert "🟡" in subject
        assert "Sistema operacional" in body
        assert "Ver Painel Executivo" in body


# ────────────── Send Function Tests ──────────────


class TestSendFunction:

    @patch("app.core.email_client.settings")
    def test_send_returns_false_when_not_configured(self, mock_settings):
        from app.core.email_client import send

        mock_settings.smtp_host = ""
        mock_settings.smtp_user = ""
        assert send("to@example.com", "Test", "<p>Hi</p>") is False

    @patch("app.core.email_client.smtplib.SMTP")
    @patch("app.core.email_client.settings")
    def test_send_success(self, mock_settings, mock_smtp_class):
        from app.core.email_client import send

        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_password = "pass123"
        mock_settings.smtp_from = "noreply@example.com"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        assert send("to@example.com", "Test Subject", "<p>Hello</p>") is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "pass123")
        mock_server.send_message.assert_called_once()

    @patch("app.core.email_client.smtplib.SMTP")
    @patch("app.core.email_client.settings")
    def test_send_returns_false_on_error(self, mock_settings, mock_smtp_class):
        from app.core.email_client import send

        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_from = ""

        mock_smtp_class.side_effect = ConnectionRefusedError("Connection refused")

        assert send("to@example.com", "Subj", "<p>Hi</p>") is False

    @patch("app.core.email_client.send")
    def test_send_to_org_admins(self, mock_send):
        from app.core.email_client import send_to_org_admins

        mock_send.return_value = True
        db = MagicMock()
        db.execute.return_value.mappings.return_value.all.return_value = [
            {"email": "admin1@test.com"},
            {"email": "admin2@test.com"},
        ]

        sent = send_to_org_admins(db, "org-1", "Subject", "<p>Body</p>", "alert")
        assert sent == 2
        assert mock_send.call_count == 2

    @patch("app.core.email_client.send")
    def test_send_to_role(self, mock_send):
        from app.core.email_client import send_to_role

        mock_send.return_value = True
        db = MagicMock()
        db.execute.return_value.mappings.return_value.all.return_value = [
            {"email": "dev@test.com"},
        ]

        sent = send_to_role(db, "org-1", "dev", "Subject", "<p>Body</p>")
        assert sent == 1

    def test_send_test_email(self):
        from app.core.email_client import send_test_email

        with patch("app.core.email_client.send", return_value=True) as mock_send:
            assert send_test_email("admin@test.com") is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert "admin@test.com" in args[0]
            assert "Teste" in args[0][1]


# ────────────── Notification Preferences API Tests ──────────────


class TestNotificationPreferencesAPI:

    def test_get_preferences_defaults(self, admin_client):
        """When no preferences exist, return defaults."""
        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: mock_db

        r = admin_client.get("/api/notifications/preferences")
        assert r.status_code == 200
        data = r.json()
        assert data["email_enabled"] is True
        assert data["alert_email"] is True
        assert data["incident_email"] is True

    def test_get_preferences_existing(self, admin_client):
        """When preferences exist, return them."""
        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "email_enabled": False,
            "alert_email": True,
            "incident_email": False,
            "review_email": True,
            "security_email": False,
            "executive_email": True,
        }
        app.dependency_overrides[get_session] = lambda: mock_db

        r = admin_client.get("/api/notifications/preferences")
        assert r.status_code == 200
        assert r.json()["email_enabled"] is False
        assert r.json()["incident_email"] is False

    def test_update_preferences_insert(self, admin_client):
        """When no preferences exist, insert new row."""
        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: mock_db

        r = admin_client.put(
            "/api/notifications/preferences",
            json={
                "email_enabled": True,
                "alert_email": True,
                "incident_email": False,
                "review_email": True,
                "security_email": True,
                "executive_email": False,
            },
        )
        assert r.status_code == 200
        assert r.json()["incident_email"] is False
        assert r.json()["executive_email"] is False
        mock_db.commit.assert_called_once()

    def test_update_preferences_update(self, admin_client):
        """When preferences exist, update them."""
        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {"id": "pref-1"}
        app.dependency_overrides[get_session] = lambda: mock_db

        r = admin_client.put(
            "/api/notifications/preferences",
            json={
                "email_enabled": False,
                "alert_email": False,
                "incident_email": False,
                "review_email": False,
                "security_email": False,
                "executive_email": False,
            },
        )
        assert r.status_code == 200
        assert r.json()["email_enabled"] is False
        mock_db.commit.assert_called_once()

    def test_dev_can_access_preferences(self, dev_client):
        """Any authenticated user can manage their preferences."""
        mock_db = MagicMock()
        mock_db.execute.return_value.mappings.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: mock_db

        r = dev_client.get("/api/notifications/preferences")
        assert r.status_code == 200


# ────────────── SMTP Config API Tests ──────────────


class TestSMTPConfigAPI:

    @patch("app.config.settings")
    def test_get_smtp_configured(self, mock_settings, admin_client):
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@gmail.com"
        mock_settings.smtp_password = "secret"
        mock_settings.smtp_from = "noreply@memora.app"

        r = admin_client.get("/api/notifications/smtp")
        assert r.status_code == 200
        data = r.json()
        assert data["configured"] is True
        assert data["smtp_host"] == "smtp.gmail.com"
        assert data["smtp_password"] == "••••••••"
        assert data["smtp_from"] == "noreply@memora.app"

    @patch("app.config.settings")
    def test_get_smtp_not_configured(self, mock_settings, admin_client):
        mock_settings.smtp_host = ""
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        mock_settings.smtp_from = ""

        r = admin_client.get("/api/notifications/smtp")
        assert r.status_code == 200
        assert r.json()["configured"] is False

    def test_smtp_admin_only(self, dev_client):
        """Non-admin users should be blocked."""
        r = dev_client.get("/api/notifications/smtp")
        assert r.status_code == 403

    @patch("app.core.email_client.send_test_email")
    def test_smtp_test_success(self, mock_send, admin_client):
        mock_send.return_value = True
        r = admin_client.post("/api/notifications/smtp/test")
        assert r.status_code == 200
        assert "teste" in r.json()["message"].lower() or "test" in r.json()["message"].lower()

    @patch("app.core.email_client.send_test_email")
    def test_smtp_test_failure(self, mock_send, admin_client):
        mock_send.return_value = False
        r = admin_client.post("/api/notifications/smtp/test")
        assert r.status_code == 500

    def test_smtp_test_admin_only(self, dev_client):
        r = dev_client.post("/api/notifications/smtp/test")
        assert r.status_code == 403
