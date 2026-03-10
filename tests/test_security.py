"""Testes de seguranca - rate limiting, refresh tokens, audit log, validacoes."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.main import app

client = TestClient(app)


# --- Rate Limiting ---

def test_rate_limit_returns_429_on_exceed():
    from slowapi.errors import RateLimitExceeded
    from app.main import _rate_limit_handler
    import json

    req = MagicMock()
    exc = MagicMock(spec=RateLimitExceeded)
    response = _rate_limit_handler(req, exc)
    assert response.status_code == 429
    body = json.loads(response.body)
    assert "limite" in body["detail"].lower()


# --- Security Headers ---

def test_security_headers_present(admin_client):
    response = admin_client.get("/api/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "strict-origin" in response.headers.get("Referrer-Policy", "")
    assert "camera=()" in response.headers.get("Permissions-Policy", "")


def test_server_header_removed(admin_client):
    response = admin_client.get("/api/health")
    assert "server" not in response.headers


# --- Payload Size Limits ---

def test_payload_limit_constants():
    from app.main import _MAX_BODY_CHAT, _MAX_BODY_INGEST, _MAX_BODY_DEFAULT
    assert _MAX_BODY_CHAT == 1 * 1024 * 1024
    assert _MAX_BODY_INGEST == 50 * 1024 * 1024
    assert _MAX_BODY_DEFAULT == 10 * 1024 * 1024


# --- Refresh Tokens ---

def test_refresh_token_hash():
    from app.core.refresh_tokens import _hash_token
    h = _hash_token("test-token")
    assert len(h) == 64
    assert _hash_token("test-token") == h


def test_refresh_token_create():
    from app.core.refresh_tokens import create_refresh_token
    mock_db = MagicMock()
    token = create_refresh_token(mock_db, "user-001", "127.0.0.1", "Mozilla/5.0")
    assert len(token) > 20
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


def test_refresh_token_validate_and_rotate():
    from app.core.refresh_tokens import validate_and_rotate
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "user_id": "user-001",
        "expires_at": datetime.utcnow() + timedelta(days=1),
        "revoked_at": None,
        "used_at": None,
        "family_id": "family-001",
    }
    new_token, user_id = validate_and_rotate(mock_db, "old-token", "127.0.0.1")
    assert user_id == "user-001"
    assert len(new_token) > 20


def test_refresh_token_replay_detection():
    from app.core.refresh_tokens import validate_and_rotate
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "user_id": "user-001",
        "expires_at": datetime.utcnow() + timedelta(days=1),
        "revoked_at": None,
        "used_at": datetime.utcnow(),
        "family_id": "family-001",
    }
    with pytest.raises(ValueError, match="Replay"):
        validate_and_rotate(mock_db, "reused-token")


def test_refresh_token_expired():
    from app.core.refresh_tokens import validate_and_rotate
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "user_id": "user-001",
        "expires_at": datetime.utcnow() - timedelta(days=1),
        "revoked_at": None,
        "used_at": None,
        "family_id": None,
    }
    with pytest.raises(ValueError, match="expirado"):
        validate_and_rotate(mock_db, "expired-token")


def test_refresh_token_revoked():
    from app.core.refresh_tokens import validate_and_rotate
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "user_id": "user-001",
        "expires_at": datetime.utcnow() + timedelta(days=1),
        "revoked_at": datetime.utcnow(),
        "used_at": None,
        "family_id": None,
    }
    with pytest.raises(ValueError, match="revogado"):
        validate_and_rotate(mock_db, "revoked-token")


def test_refresh_token_not_found():
    from app.core.refresh_tokens import validate_and_rotate
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = None
    with pytest.raises(ValueError):
        validate_and_rotate(mock_db, "unknown-token")


def test_revoke_token():
    from app.core.refresh_tokens import revoke_token
    mock_db = MagicMock()
    revoke_token(mock_db, "some-token")
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


def test_revoke_all_user_tokens():
    from app.core.refresh_tokens import revoke_all_user_tokens
    mock_db = MagicMock()
    mock_db.execute.return_value.rowcount = 3
    count = revoke_all_user_tokens(mock_db, "user-001")
    assert count == 3


# --- Auth endpoints: refresh + logout ---

@patch("app.api.routes.auth.validate_and_rotate")
def test_auth_refresh_success(mock_rotate):
    mock_rotate.return_value = ("new-token-xyz", "user-001")
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    response = client.post("/api/auth/refresh", json={"refresh_token": "old-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["refresh_token"] == "new-token-xyz"
    app.dependency_overrides.clear()


@patch("app.api.routes.auth.validate_and_rotate")
def test_auth_refresh_invalid(mock_rotate):
    mock_rotate.side_effect = ValueError("Token invalido")
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    response = client.post("/api/auth/refresh", json={"refresh_token": "bad-token"})
    assert response.status_code == 401
    app.dependency_overrides.clear()


@patch("app.api.routes.auth.revoke_refresh_token")
def test_auth_logout(mock_revoke):
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    response = client.post("/api/auth/logout", json={"refresh_token": "some-token"})
    assert response.status_code == 200
    mock_revoke.assert_called_once()
    app.dependency_overrides.clear()


# --- Audit Log ---

def test_audit_log_action():
    from app.core.audit import log_action
    mock_db = MagicMock()
    log_action(
        mock_db,
        user_id="u-001",
        org_id="org-001",
        action="auth.login",
        ip_address="127.0.0.1",
    )
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


def test_audit_log_never_raises():
    from app.core.audit import log_action
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB error")
    # Should not raise
    log_action(mock_db, user_id="u-001", org_id="org-001", action="test")


def test_audit_log_get_entries():
    from app.core.audit import get_audit_log
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = [
        {
            "id": 1,
            "action": "auth.login",
            "org_id": "org-001",
            "user_id": "u-001",
            "resource_type": None,
            "resource_id": None,
            "detail": None,
            "ip_address": "127.0.0.1",
            "created_at": datetime.utcnow(),
        }
    ]
    entries = get_audit_log(mock_db, "org-001", action="auth.login")
    assert len(entries) == 1
    assert entries[0]["action"] == "auth.login"


def test_audit_route_blocked_for_suporte(suporte_client):
    response = suporte_client.get("/api/admin/audit")
    assert response.status_code == 403


def test_audit_route_allowed_for_admin(admin_client):
    response = admin_client.get("/api/admin/audit")
    # 200 or 500 (mock DB), but never 401/403
    assert response.status_code not in (401, 403)


# --- Encryption Key Validation ---

def test_encryption_validate_callable():
    from app.core.encryption import validate_encryption_key
    assert callable(validate_encryption_key)


def test_encryption_missing_key_exits():
    with patch("app.core.encryption.settings") as mock_settings:
        mock_settings.llm_encryption_key = None
        import app.core.encryption as enc
        old_fernet = enc._fernet
        enc._fernet = None
        try:
            with pytest.raises(SystemExit):
                enc._get_fernet()
        finally:
            enc._fernet = old_fernet


# --- DAST SSRF Prevention ---

def test_dast_blocks_private_ips():
    from app.core.dast_scanner import _is_blocked_host
    assert _is_blocked_host("127.0.0.1") is True
    assert _is_blocked_host("10.0.0.1") is True
    assert _is_blocked_host("192.168.1.1") is True
    assert _is_blocked_host("localhost") is True


def test_dast_blocks_loopback():
    from app.core.dast_scanner import _is_blocked_host
    assert _is_blocked_host("::1") is True


def test_dast_allows_public_ips():
    from app.core.dast_scanner import _is_blocked_host
    assert _is_blocked_host("8.8.8.8") is False
    assert _is_blocked_host("1.1.1.1") is False


def test_dast_validate_url_rejects_ftp():
    from app.core.dast_scanner import validate_target_url
    error = validate_target_url("ftp://example.com")
    assert error is not None


def test_dast_validate_url_rejects_private():
    from app.core.dast_scanner import validate_target_url
    error = validate_target_url("http://192.168.1.1:8080")
    assert error is not None


# --- Repo Ingestion Size Validation ---

def test_ingest_max_repo_size_constants():
    from app.api.routes.ingest import MAX_REPO_SIZE_MB, MAX_REPO_FILES
    assert MAX_REPO_SIZE_MB == 500
    assert MAX_REPO_FILES == 50_000


@patch("app.api.routes.ingest.httpx.get")
def test_check_github_repo_size_rejects_large(mock_get):
    from fastapi import HTTPException
    from app.api.routes.ingest import _check_github_repo_size

    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"size": 600 * 1024},
    )
    with pytest.raises(HTTPException) as exc_info:
        _check_github_repo_size("https://github.com/owner/repo")
    assert exc_info.value.status_code == 400
    assert "500MB" in exc_info.value.detail


@patch("app.api.routes.ingest.httpx.get")
def test_check_github_repo_size_allows_small(mock_get):
    from app.api.routes.ingest import _check_github_repo_size

    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"size": 100 * 1024},
    )
    _check_github_repo_size("https://github.com/owner/repo")


# --- Rate Limit Constants ---

def test_rate_limit_constants():
    from app.core.rate_limit import AUTH_LIMIT, REGISTER_LIMIT, ASK_LIMIT, INGEST_LIMIT
    assert AUTH_LIMIT == "10/minute"
    assert REGISTER_LIMIT == "5/minute"
    assert ASK_LIMIT == "60/minute"
    assert INGEST_LIMIT == "10/minute"
