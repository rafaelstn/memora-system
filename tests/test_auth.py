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


# --- API: /auth/register with invite + product_id ---
@patch("app.api.routes.auth._create_supabase_user")
def test_register_with_invite_creates_product_membership(mock_create):
    mock_create.return_value = "supabase-uid-002"

    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 1  # not first user
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # Mock invite query
    invite_data = {
        "id": "inv-001",
        "org_id": "org-001",
        "role": "dev",
        "email": "invited@example.com",
        "product_id": "prod-001",
        "created_by": "u-admin-001",
    }
    mock_db.execute.return_value.mappings.return_value.first.return_value = invite_data

    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Invited User",
            "email": "invited@example.com",
            "password": "secure123",
            "invite_token": "valid-token-123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "dev"

    # Verify product_membership INSERT was called (check by params containing product_id)
    execute_calls = mock_db.execute.call_args_list
    membership_insert = [
        c for c in execute_calls
        if len(c.args) > 1 and isinstance(c.args[1], dict) and "product_id" in c.args[1] and c.args[1]["product_id"] == "prod-001"
    ]
    assert len(membership_insert) > 0, "Expected product_memberships INSERT with product_id=prod-001"
    app.dependency_overrides.clear()


@patch("app.api.routes.auth._create_supabase_user")
def test_register_with_invite_without_product_id(mock_create):
    mock_create.return_value = "supabase-uid-003"

    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 1
    mock_db.query.return_value.filter.return_value.first.return_value = None

    invite_data = {
        "id": "inv-002",
        "org_id": "org-001",
        "role": "suporte",
        "email": None,
        "product_id": None,
        "created_by": "u-admin-001",
    }
    mock_db.execute.return_value.mappings.return_value.first.return_value = invite_data

    app.dependency_overrides[get_session] = lambda: mock_db

    response = client.post(
        "/api/auth/register",
        json={
            "name": "No Product User",
            "email": "noproduct@example.com",
            "password": "secure123",
            "invite_token": "valid-token-456",
        },
    )
    assert response.status_code == 200

    # No product_memberships INSERT
    execute_calls = mock_db.execute.call_args_list
    membership_insert = [c for c in execute_calls if "product_memberships" in str(c)]
    assert len(membership_insert) == 0, "Should not insert product_membership when no product_id"
    app.dependency_overrides.clear()


# --- API: /admin/invites with product_id ---
def test_create_invite_with_product_id(admin_client):
    response = admin_client.post("/api/admin/invites", json={
        "role": "dev",
        "email": "test@example.com",
        "product_id": "prod-test-001",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "dev"
    assert data["product_id"] == "prod-test-001"
    assert "invite_url" in data


def test_create_invite_without_product_id(admin_client):
    response = admin_client.post("/api/admin/invites", json={
        "role": "suporte",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] is None


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
