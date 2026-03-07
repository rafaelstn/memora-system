"""Testes do sistema de autenticacao Supabase Auth."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.auth import decode_supabase_jwt
from app.main import app

client = TestClient(app)


# --- Unit: Supabase JWT decode ---
def test_decode_invalid_token():
    assert decode_supabase_jwt("invalid.token.here") is None


# --- API: protected endpoint without token ---
def test_protected_endpoint_requires_auth():
    app.dependency_overrides.clear()
    response = client.post("/api/ask", json={"question": "test", "repo_name": "test"})
    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_admin_endpoint_requires_auth():
    app.dependency_overrides.clear()
    response = client.get("/api/admin/users")
    assert response.status_code == 401
    app.dependency_overrides.clear()


# --- API: /auth/me ---
def test_me_with_valid_token(admin_client):
    response = admin_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "admin"
    assert "github_connected" in data


# --- API: /auth/register (primeiro usuario = admin) ---
@patch("app.api.routes.auth._create_supabase_user")
def test_register_first_user_becomes_admin(mock_create):
    mock_create.return_value = "supabase-uid-001"

    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/auth/register",
        json={"name": "First Admin", "email": "first@example.com", "password": "secure123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data["email"] == "first@example.com"
    app.dependency_overrides.clear()


# --- API: /auth/register (segundo usuario sem invite = 403) ---
@patch("app.api.routes.auth._create_supabase_user")
def test_register_without_invite_forbidden(mock_create):
    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 1
    mock_db.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/auth/register",
        json={"name": "User Two", "email": "two@example.com", "password": "secure123"},
    )
    assert response.status_code == 403
    assert "convite" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


# --- API: /health/admin-exists ---
def test_health_admin_exists_empty():
    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 0

    with patch("app.main.SessionLocal", return_value=mock_db):
        response = client.get("/api/health/admin-exists")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["requires_invite"] is False
