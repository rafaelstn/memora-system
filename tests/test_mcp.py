"""Testes para o MCP Server."""

import hashlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_data_session, get_session
from app.main import app
from tests.conftest import _fake_user


def _mock_session() -> MagicMock:
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.execute.return_value.mappings.return_value.all.return_value = []
    session.execute.return_value.mappings.return_value.first.return_value = None
    session.execute.return_value.rowcount = 1
    return session


@pytest.fixture()
def admin_client():
    fake = _fake_user("admin")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def dev_client():
    fake = _fake_user("dev")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def suporte_client():
    fake = _fake_user("suporte")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- GET /mcp/health ---

def test_mcp_health():
    """Health endpoint returns 6 tools."""
    client = TestClient(app)
    resp = client.get("/mcp/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["tools"] == 6
    assert data["version"] == "1.0"


# --- Tool call without token ---

def test_tool_call_no_token():
    """Request without token returns 401."""
    client = TestClient(app)
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    resp = client.post("/mcp/tools/call", json={"name": "search_similar_code", "arguments": {"query": "test"}})
    assert resp.status_code == 401
    app.dependency_overrides.clear()


def test_tool_call_invalid_token():
    """Request with invalid token returns 401."""
    client = TestClient(app)
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    resp = client.post(
        "/mcp/tools/call",
        json={"name": "search_similar_code", "arguments": {"query": "test"}},
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert resp.status_code == 401
    app.dependency_overrides.clear()


# --- Tool call with valid token ---

@patch("mcp.tools.search_code.Embedder")
def test_search_similar_code_with_valid_token(mock_embedder_cls):
    """search_similar_code returns chunks from DB."""
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536
    mock_embedder_cls.return_value = mock_embedder

    valid_token = "mcp_test_token_123"
    token_hash = hashlib.sha256(valid_token.encode()).hexdigest()

    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Token validation
                result.mappings.return_value.first.return_value = {
                    "org_id": "org-test-001",
                    "user_id": "u-test-001",
                }
            else:
                # Code search
                result.mappings.return_value.all.return_value = [{
                    "repo_name": "test-repo",
                    "file_path": "services/pricing.py",
                    "chunk_name": "calc_discount",
                    "chunk_type": "function",
                    "content": "def calc_discount(): pass",
                    "score": 0.85,
                }]
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    client = TestClient(app)

    resp = client.post(
        "/mcp/tools/call",
        json={"name": "search_similar_code", "arguments": {"query": "calculo de desconto"}},
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "pricing" in data["result"]
    app.dependency_overrides.clear()


@patch("mcp.tools.get_rules.Embedder")
def test_get_business_rules_with_context(mock_embedder_cls):
    """get_business_rules returns rules relevant to context."""
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536
    mock_embedder_cls.return_value = mock_embedder

    valid_token = "mcp_test_token_456"
    token_hash = hashlib.sha256(valid_token.encode()).hexdigest()

    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.mappings.return_value.first.return_value = {
                    "org_id": "org-test-001",
                    "user_id": "u-test-001",
                }
            else:
                result.mappings.return_value.all.return_value = [{
                    "id": "rule-001",
                    "rule_type": "calculation",
                    "title": "Desconto progressivo",
                    "plain_english": "Se pedido > R$500, aplica 10%",
                    "conditions": [{"if": "pedido > 500", "then": "desconto = 10%"}],
                    "confidence": 0.9,
                    "score": 0.88,
                }]
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    client = TestClient(app)

    resp = client.post(
        "/mcp/tools/call",
        json={"name": "get_business_rules", "arguments": {"context": "desconto para pedidos"}},
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Desconto" in data["result"]
    app.dependency_overrides.clear()


def test_get_team_patterns_returns_result():
    """get_team_patterns returns patterns from ADRs and code."""
    valid_token = "mcp_test_token_789"

    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.mappings.return_value.first.return_value = {
                    "org_id": "org-test-001",
                    "user_id": "u-test-001",
                }
            elif call_count == 2:
                # ADRs
                result.mappings.return_value.all.return_value = [{
                    "title": "Usar snake_case",
                    "summary": "Todos os nomes de funcoes devem usar snake_case",
                }]
            else:
                # Code chunks
                result.mappings.return_value.all.return_value = []
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    client = TestClient(app)

    with patch("mcp.tools.get_patterns.Embedder") as MockEmb:
        mock_emb = MagicMock()
        mock_emb.embed_text.return_value = [0.1] * 1536
        MockEmb.return_value = mock_emb

        with patch("mcp.tools.get_patterns.llm_router") as mock_llm:
            mock_llm.complete.return_value = {"content": "Naming: snake_case\nEstrutura: modular"}

            resp = client.post(
                "/mcp/tools/call",
                json={"name": "get_team_patterns", "arguments": {"context": "novo endpoint"}},
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            assert resp.status_code == 200
            assert "snake_case" in resp.json()["result"]

    app.dependency_overrides.clear()


# --- Token management ---

def test_generate_mcp_token(admin_client):
    """Admin can generate MCP token."""
    resp = admin_client.post("/api/mcp/token")
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["token"].startswith("mcp_")
    assert "id" in data


def test_generate_mcp_token_dev(dev_client):
    """Dev can generate MCP token."""
    resp = dev_client.post("/api/mcp/token")
    assert resp.status_code == 200
    assert resp.json()["token"].startswith("mcp_")


def test_generate_mcp_token_suporte_denied(suporte_client):
    """Suporte cannot generate MCP token."""
    resp = suporte_client.post("/api/mcp/token")
    assert resp.status_code in (401, 403)


def test_revoke_token_no_active(admin_client):
    """Revoking when no active token returns 404."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.rowcount = 0
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.delete("/api/mcp/token")
    assert resp.status_code == 404


def test_mcp_token_status(admin_client):
    """Token status returns has_token status."""
    resp = admin_client.get("/api/mcp/token/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "has_token" in data
