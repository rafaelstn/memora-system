"""Testes para rotas Enterprise: setup, health check, health log."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_data_session, get_session
from app.main import app
from app.models.user import User


def _fake_admin():
    user = MagicMock(spec=User)
    user.id = "u-test-001"
    user.name = "Admin Test"
    user.email = "admin@test.com"
    user.role = "admin"
    user.avatar_url = None
    user.is_active = True
    user.github_connected = False
    user.org_id = "org-test-001"
    return user


def _fake_dev():
    user = MagicMock(spec=User)
    user.id = "u-test-002"
    user.name = "Dev Test"
    user.email = "dev@test.com"
    user.role = "dev"
    user.avatar_url = None
    user.is_active = True
    user.github_connected = False
    user.org_id = "org-test-001"
    return user


def _mock_session():
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session


def _admin_client():
    app.dependency_overrides[get_current_user] = _fake_admin
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    client = TestClient(app)
    return client


def _dev_client():
    app.dependency_overrides[get_current_user] = _fake_dev
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    client = TestClient(app)
    return client


def _cleanup():
    app.dependency_overrides.clear()


# ---------- Health Check Route ----------

@patch("app.api.routes.enterprise.check_health")
def test_health_check_admin(mock_check):
    mock_check.return_value = {
        "status": "ok",
        "response_time_ms": 42,
        "error": None,
        "previous_status": "ok",
    }
    client = _admin_client()
    try:
        res = client.post("/api/enterprise/health-check")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["response_time_ms"] == 42
        mock_check.assert_called_once_with("org-test-001")
    finally:
        _cleanup()


@patch("app.api.routes.enterprise.check_health")
def test_health_check_error_status(mock_check):
    mock_check.return_value = {
        "status": "error",
        "response_time_ms": 10001,
        "error": "connection refused",
        "previous_status": "ok",
    }
    client = _admin_client()
    try:
        res = client.post("/api/enterprise/health-check")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error"
        assert data["error"] == "connection refused"
    finally:
        _cleanup()


def test_health_check_dev_forbidden():
    client = _dev_client()
    try:
        res = client.post("/api/enterprise/health-check")
        assert res.status_code == 403
    finally:
        _cleanup()


# ---------- Health Log Route ----------

@patch("app.api.routes.enterprise.get_health_log")
def test_health_log_returns_entries(mock_log):
    mock_log.return_value = [
        {"status": "ok", "response_time_ms": 30, "error": None, "checked_at": "2026-03-10 12:00:00"},
        {"status": "error", "response_time_ms": 10000, "error": "timeout", "checked_at": "2026-03-10 11:30:00"},
    ]
    client = _admin_client()
    try:
        res = client.get("/api/enterprise/health-log?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["status"] == "ok"
        mock_log.assert_called_once_with("org-test-001", limit=10)
    finally:
        _cleanup()


def test_health_log_dev_forbidden():
    client = _dev_client()
    try:
        res = client.get("/api/enterprise/health-log")
        assert res.status_code == 403
    finally:
        _cleanup()


# ---------- Health Transition Email ----------

@patch("app.api.routes.enterprise.check_health")
@patch("app.api.routes.enterprise._notify_health_transition")
def test_health_check_triggers_email_on_transition(mock_notify, mock_check):
    mock_check.return_value = {
        "status": "error",
        "response_time_ms": 5000,
        "error": "connection refused",
        "previous_status": "ok",
    }
    client = _admin_client()
    try:
        res = client.post("/api/enterprise/health-check")
        assert res.status_code == 200
        mock_notify.assert_called_once_with("org-test-001", "error", "connection refused")
    finally:
        _cleanup()


@patch("app.api.routes.enterprise.check_health")
@patch("app.api.routes.enterprise._notify_health_transition")
def test_health_check_no_email_when_same_status(mock_notify, mock_check):
    mock_check.return_value = {
        "status": "ok",
        "response_time_ms": 25,
        "error": None,
        "previous_status": "ok",
    }
    client = _admin_client()
    try:
        res = client.post("/api/enterprise/health-check")
        assert res.status_code == 200
        mock_notify.assert_not_called()
    finally:
        _cleanup()


@patch("app.api.routes.enterprise.check_health")
@patch("app.api.routes.enterprise._notify_health_transition")
def test_health_check_email_on_recovery(mock_notify, mock_check):
    mock_check.return_value = {
        "status": "ok",
        "response_time_ms": 35,
        "error": None,
        "previous_status": "error",
    }
    client = _admin_client()
    try:
        res = client.post("/api/enterprise/health-check")
        assert res.status_code == 200
        mock_notify.assert_called_once_with("org-test-001", "ok", None)
    finally:
        _cleanup()


# ---------- Status Route (includes health fields) ----------

@patch("app.api.routes.enterprise.get_setup_status")
def test_status_includes_health_fields(mock_status):
    mock_status.return_value = {
        "configured": True,
        "setup_complete": True,
        "last_health_status": "ok",
        "last_health_check": "2026-03-10 12:00:00",
        "last_health_error": None,
        "created_at": "2026-03-01",
        "updated_at": "2026-03-10",
    }
    client = _admin_client()
    try:
        res = client.get("/api/enterprise/status")
        assert res.status_code == 200
        data = res.json()
        assert data["last_health_status"] == "ok"
        assert data["last_health_check"] is not None
    finally:
        _cleanup()


# ---------- Test Connection Route ----------

@patch("app.api.routes.enterprise.test_connection")
def test_connection_route(mock_test):
    mock_test.return_value = {"success": True, "message": "Conexao OK", "version": "16.1"}
    client = _admin_client()
    try:
        res = client.post("/api/enterprise/test-connection", json={
            "host": "db.example.com",
            "port": 5432,
            "database": "memora",
            "username": "user",
            "password": "pass",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
    finally:
        _cleanup()


# ---------- Email Template Tests ----------

def test_enterprise_db_down_email_template():
    from app.core.email_client import build_enterprise_db_down_email

    subject, body = build_enterprise_db_down_email("Acme Corp", "connection refused", "http://localhost:3000/setup/enterprise")
    assert "indisponivel" in subject.lower() or "indisponivel" in subject
    assert "Acme Corp" in subject
    assert "connection refused" in body
    assert "Verificar Configuracao" in body


def test_enterprise_db_recovered_email_template():
    from app.core.email_client import build_enterprise_db_recovered_email

    subject, body = build_enterprise_db_recovered_email("Acme Corp", "http://localhost:3000/dashboard")
    assert "recuperado" in subject.lower() or "recuperado" in subject
    assert "Acme Corp" in subject
    assert "voltou a responder" in body
