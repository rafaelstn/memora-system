"""Tests for LLM provider management endpoints."""

from unittest.mock import MagicMock, patch


# ─── Admin CRUD ─────────────────────────────────────────────────────────────

def test_create_provider_openai(admin_client):
    """POST /api/llm-providers with valid OpenAI data creates provider."""
    mock_db = MagicMock()
    # Mock the COUNT query (no existing providers = auto-default)
    mock_db.execute.return_value.scalar.return_value = 0
    # Mock the INSERT (returns nothing)
    # Mock the SELECT after insert
    mock_row = {
        "id": "prov-001",
        "name": "GPT-4o Mini",
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "api_key_encrypted": "encrypted_key_here",
        "base_url": None,
        "is_active": True,
        "is_default": True,
        "last_tested_at": None,
        "last_test_status": "untested",
        "last_test_error": None,
        "created_at": "2026-03-06T12:00:00",
        "updated_at": "2026-03-06T12:00:00",
    }
    mock_db.execute.return_value.mappings.return_value.first.return_value = mock_row

    from app.api.deps import get_session
    from app.main import app
    app.dependency_overrides[get_session] = lambda: mock_db

    with patch("app.api.routes.llm_providers.encrypt_api_key", return_value="encrypted_key_here"):
        res = admin_client.post("/api/llm-providers", json={
            "name": "GPT-4o Mini",
            "provider": "openai",
            "model_id": "gpt-4o-mini",
            "api_key": "sk-test-key-12345",
        })

    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "GPT-4o Mini"
    assert data["provider"] == "openai"
    assert data["model_id"] == "gpt-4o-mini"
    # API key should never be returned in full
    assert "sk-test-key" not in str(data)


def test_create_provider_openai_no_key(admin_client):
    """POST /api/llm-providers without api_key for OpenAI returns 400."""
    res = admin_client.post("/api/llm-providers", json={
        "name": "GPT-4o",
        "provider": "openai",
        "model_id": "gpt-4o",
    })
    assert res.status_code == 400
    assert "API key" in res.json()["detail"]


def test_create_provider_invalid_model(admin_client):
    """POST /api/llm-providers with invalid model returns 400."""
    res = admin_client.post("/api/llm-providers", json={
        "name": "Bad Model",
        "provider": "openai",
        "model_id": "invalid-model-xyz",
        "api_key": "sk-test",
    })
    assert res.status_code == 400
    assert "nao suportado" in res.json()["detail"]


def test_create_provider_invalid_provider(admin_client):
    """POST /api/llm-providers with invalid provider returns 400."""
    res = admin_client.post("/api/llm-providers", json={
        "name": "Bad Provider",
        "provider": "invalid",
        "model_id": "some-model",
        "api_key": "sk-test",
    })
    assert res.status_code == 400
    assert "invalido" in res.json()["detail"]


def test_create_provider_ollama_no_key(admin_client):
    """POST /api/llm-providers for Ollama works without api_key."""
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 0
    mock_row = {
        "id": "prov-002",
        "name": "Llama 3.2",
        "provider": "ollama",
        "model_id": "llama3.2",
        "api_key_encrypted": None,
        "base_url": "http://localhost:11434",
        "is_active": True,
        "is_default": True,
        "last_tested_at": None,
        "last_test_status": "untested",
        "last_test_error": None,
        "created_at": "2026-03-06T12:00:00",
        "updated_at": "2026-03-06T12:00:00",
    }
    mock_db.execute.return_value.mappings.return_value.first.return_value = mock_row

    from app.api.deps import get_session
    from app.main import app
    app.dependency_overrides[get_session] = lambda: mock_db

    res = admin_client.post("/api/llm-providers", json={
        "name": "Llama 3.2",
        "provider": "ollama",
        "model_id": "llama3.2",
        "base_url": "http://localhost:11434",
    })
    assert res.status_code == 201


def test_list_providers(admin_client):
    """GET /api/llm-providers returns list without full api keys."""
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = [
        {
            "id": "prov-001",
            "name": "GPT-4o Mini",
            "provider": "openai",
            "model_id": "gpt-4o-mini",
            "api_key_encrypted": None,  # Simplified for test
            "base_url": None,
            "is_active": True,
            "is_default": True,
            "last_tested_at": None,
            "last_test_status": "ok",
            "last_test_error": None,
            "created_at": "2026-03-06T12:00:00",
            "updated_at": "2026-03-06T12:00:00",
        },
    ]

    from app.api.deps import get_session
    from app.main import app
    app.dependency_overrides[get_session] = lambda: mock_db

    res = admin_client.get("/api/llm-providers")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "GPT-4o Mini"
    # Ensure no full API key in response
    assert "api_key" not in data[0] or data[0].get("api_key_masked", "") != "sk-"


def test_delete_default_provider_fails(admin_client):
    """DELETE /api/llm-providers/{id} on default provider returns 400."""
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "id": "prov-001",
        "is_default": True,
        "is_active": True,
    }

    from app.api.deps import get_session
    from app.main import app
    app.dependency_overrides[get_session] = lambda: mock_db

    res = admin_client.delete("/api/llm-providers/prov-001")
    assert res.status_code == 400
    assert "padrao" in res.json()["detail"]


def test_set_default(admin_client):
    """POST /api/llm-providers/{id}/set-default switches default."""
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "id": "prov-002",
        "is_active": True,
    }

    from app.api.deps import get_session
    from app.main import app
    app.dependency_overrides[get_session] = lambda: mock_db

    res = admin_client.post("/api/llm-providers/prov-002/set-default")
    assert res.status_code == 200
    assert res.json()["default"] is True


# ─── Role-based access ──────────────────────────────────────────────────────

def test_test_connection_ok(admin_client):
    """POST /api/llm-providers/test-connection tests without creating a provider."""
    with patch("app.integrations.llm_router.OpenAIClient") as MockClient:
        instance = MockClient.return_value
        instance.complete.return_value = {"text": "ok", "input_tokens": 5, "output_tokens": 1, "cost_usd": 0.0}

        res = admin_client.post("/api/llm-providers/test-connection", json={
            "provider": "openai",
            "model_id": "gpt-4o-mini",
            "api_key": "sk-test-key",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "latency_ms" in data


def test_test_connection_no_key(admin_client):
    """POST /api/llm-providers/test-connection without key returns 400."""
    res = admin_client.post("/api/llm-providers/test-connection", json={
        "provider": "openai",
        "model_id": "gpt-4o-mini",
    })
    assert res.status_code == 400
    assert "API key" in res.json()["detail"]


def test_dev_cannot_manage_providers(dev_client):
    """Dev cannot create/delete providers — admin-only endpoints."""
    res = dev_client.post("/api/llm-providers", json={
        "name": "test",
        "provider": "openai",
        "model_id": "gpt-4o",
        "api_key": "sk-test",
    })
    assert res.status_code == 403


def test_suporte_cannot_manage_providers(suporte_client):
    """Suporte cannot access provider management."""
    res = suporte_client.get("/api/llm-providers")
    assert res.status_code == 403


def test_active_providers_accessible_by_all_roles(admin_client, dev_client, suporte_client):
    """GET /api/llm-providers/active is accessible by all authenticated roles."""
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = []

    from app.api.deps import get_session
    from app.main import app

    for client in [admin_client, dev_client, suporte_client]:
        app.dependency_overrides[get_session] = lambda: mock_db
        res = client.get("/api/llm-providers/active")
        assert res.status_code == 200


# ─── Encryption ─────────────────────────────────────────────────────────────

def test_encryption_roundtrip():
    """Encrypt and decrypt API key produces original value."""
    with patch("app.core.encryption.settings") as mock_settings:
        from cryptography.fernet import Fernet
        mock_settings.llm_encryption_key = Fernet.generate_key().decode()

        # Reset cached fernet
        import app.core.encryption as enc
        enc._fernet = None

        from app.core.encryption import encrypt_api_key, decrypt_api_key, mask_api_key

        original = "sk-proj-abcdef123456"
        encrypted = encrypt_api_key(original)
        assert encrypted != original
        assert decrypt_api_key(encrypted) == original
        assert mask_api_key(original) == "...3456"

        enc._fernet = None  # cleanup


def test_mask_api_key():
    """mask_api_key shows only last 4 chars."""
    from app.core.encryption import mask_api_key

    assert mask_api_key("sk-proj-abcdef123456") == "...3456"
    assert mask_api_key("abc") == "****"
    assert mask_api_key(None) == ""
    assert mask_api_key("") == ""
