"""Testes da integracao GitHub (endpoints)."""
from unittest.mock import MagicMock, patch

import httpx


# --- POST /integrations/github com token valido ---
def test_connect_github_valid_token(admin_client):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "login": "testuser",
        "avatar_url": "https://avatars.githubusercontent.com/u/123",
    }
    mock_response.headers = {"x-oauth-scopes": "repo, read:org"}

    with patch("app.api.routes.integrations.httpx.get", return_value=mock_response):
        response = admin_client.post(
            "/api/integrations/github",
            json={"token": "ghp_valid_token_here"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["github_login"] == "testuser"


# --- POST /integrations/github com token invalido ---
def test_connect_github_invalid_token(admin_client):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    with patch("app.api.routes.integrations.httpx.get", return_value=mock_response):
        response = admin_client.post(
            "/api/integrations/github",
            json={"token": "ghp_invalid"},
        )

    assert response.status_code == 400
    assert "inválido" in response.json()["detail"].lower()


# --- POST /integrations/github com role dev = 403 ---
def test_connect_github_forbidden_for_dev(dev_client):
    response = dev_client.post(
        "/api/integrations/github",
        json={"token": "ghp_any"},
    )
    assert response.status_code == 403


# --- GET /integrations/github status ---
def test_get_github_status_not_connected(admin_client):
    from app.api.deps import get_session
    from app.main import app

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_db

    response = admin_client.get("/api/integrations/github")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
