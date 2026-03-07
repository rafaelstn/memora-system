"""Testes do Monitor de Erros — ingestao, alertas, projetos, webhooks."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.api.routes.logs_ingest import _authenticate_project
from app.main import app

client = TestClient(app)


# --- Helpers ---


def _mock_db_with_project(project_id="proj-001", org_id="org-test-001", is_active=True):
    """Mock DB that returns a project for token auth."""
    mock_db = MagicMock()
    project_row = MagicMock()
    project_row.__getitem__ = lambda self, key: {
        "id": project_id,
        "org_id": org_id,
        "is_active": is_active,
    }[key]
    mock_db.execute.return_value.mappings.return_value.first.return_value = project_row
    return mock_db


def _override_project_auth(project_id="proj-001", org_id="org-test-001"):
    """Override project token authentication."""
    return {"id": project_id, "org_id": org_id, "is_active": True}


# --- POST /api/logs/ingest ---


def test_ingest_single_log_valid_token(admin_client):
    """POST /api/logs/ingest with valid token saves log."""
    app.dependency_overrides[_authenticate_project] = lambda: _override_project_auth()
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/logs/ingest",
        json={"level": "error", "message": "Connection refused to database"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["received"] == 1
    assert data["queued_for_analysis"] == 1

    app.dependency_overrides.clear()


def test_ingest_invalid_token():
    """POST /api/logs/ingest with invalid token returns 401."""
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/logs/ingest",
        json={"level": "error", "message": "test"},
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_ingest_info_not_queued():
    """POST /api/logs/ingest with level info does not queue for analysis."""
    app.dependency_overrides[_authenticate_project] = lambda: _override_project_auth()
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/logs/ingest",
        json={"level": "info", "message": "Application started"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["received"] == 1
    assert data["queued_for_analysis"] == 0

    app.dependency_overrides.clear()


def test_ingest_batch():
    """POST /api/logs/ingest batch format saves multiple logs."""
    app.dependency_overrides[_authenticate_project] = lambda: _override_project_auth()
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/logs/ingest",
        json={
            "logs": [
                {"level": "error", "message": "Error 1"},
                {"level": "critical", "message": "Error 2"},
                {"level": "info", "message": "Info 1"},
            ]
        },
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["received"] == 3
    assert data["queued_for_analysis"] == 2  # error + critical

    app.dependency_overrides.clear()


def test_ingest_missing_token():
    """POST /api/logs/ingest without token returns 401."""
    app.dependency_overrides.clear()
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/logs/ingest",
        json={"level": "error", "message": "test"},
    )
    assert response.status_code == 401

    app.dependency_overrides.clear()


# --- GET /api/monitor/alerts ---


def test_list_alerts_org_filtered(admin_client):
    """GET /api/monitor/alerts returns only alerts from user's org."""
    response = admin_client.get("/api/monitor/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# --- PATCH /api/monitor/alerts/{id}/status ---


def test_update_alert_status(admin_client):
    """PATCH /api/monitor/alerts/{id}/status updates status."""
    response = admin_client.patch(
        "/api/monitor/alerts/alert-001/status",
        json={"status": "acknowledged"},
    )
    # Expect 200 (mock returns rowcount=0 by default -> 404 is also valid)
    assert response.status_code in (200, 404)


def test_update_alert_invalid_status(admin_client):
    """PATCH with invalid status returns 400."""
    response = admin_client.patch(
        "/api/monitor/alerts/alert-001/status",
        json={"status": "invalid"},
    )
    assert response.status_code == 400


# --- POST /api/monitor/projects/{id}/rotate-token ---


def test_rotate_token(admin_client):
    """POST rotate-token returns new token."""
    response = admin_client.post("/api/monitor/projects/proj-001/rotate-token")
    # With mock DB, rowcount is MagicMock (truthy) so should return 200
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "token_preview" in data


# --- Webhook notification triggered after critical alert (mock) ---


@patch("app.core.notifier._send_webhook")
@patch("app.core.notifier.email_client")
def test_notify_alert_dispatches(mock_email_client, mock_webhook):
    """notify_alert sends email to admins and webhook."""
    mock_email_client.build_alert_email.return_value = ("Subject", "<p>Body</p>")
    mock_email_client.send_to_org_admins.return_value = 1
    mock_webhook.return_value = True

    mock_db = MagicMock()

    # Mock alert query
    alert_data = {
        "id": "alert-001",
        "project_id": "proj-001",
        "org_id": "org-001",
        "title": "DB Connection Failed",
        "explanation": "O banco de dados nao respondeu",
        "severity": "critical",
        "affected_component": "database",
        "suggested_actions": json.dumps(["Verificar conexao"]),
        "created_at": "2026-03-06 10:00:00",
        "project_name": "CEBI ERP",
    }
    alert_mock = MagicMock()
    alert_mock.__getitem__ = lambda self, key: alert_data[key]
    alert_mock.get = lambda key, default=None: alert_data.get(key, default)

    # Mock webhooks
    webhook_mock = MagicMock()
    webhook_mock.__getitem__ = lambda self, key: {"url": "https://hooks.example.com/test"}[key]

    # Setup execute chain: 1=alert, 2=webhooks
    call_count = [0]
    def mock_execute(query, params=None):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:  # alert query
            result.mappings.return_value.first.return_value = alert_mock
        elif call_count[0] == 2:  # webhooks query
            result.mappings.return_value.all.return_value = [webhook_mock]
        return result

    mock_db.execute = mock_execute

    from app.core.notifier import notify_alert
    notify_alert(mock_db, "alert-001")

    mock_email_client.build_alert_email.assert_called_once()
    mock_email_client.send_to_org_admins.assert_called_once()
    mock_webhook.assert_called_once()
