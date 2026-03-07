"""Testes para o modulo de Geracao de Codigo."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_session
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


# --- POST /api/codegen/generate ---

@patch("app.core.code_generator.search_similar_code_raw")
@patch("app.core.code_generator.get_business_rules_raw")
@patch("app.core.code_generator.get_architecture_decisions_raw")
@patch("app.core.code_generator.get_environment_context")
@patch("app.core.code_generator.llm_router")
def test_generate_code_streaming(
    mock_llm, mock_env, mock_decisions, mock_rules, mock_search, admin_client
):
    """POST /api/codegen/generate returns streaming response."""
    mock_search.return_value = [{
        "repo_name": "test-repo", "file_path": "pricing.py",
        "chunk_name": "calc", "content": "def calc(): pass", "score": 0.8,
    }]
    mock_rules.return_value = [{
        "id": "r1", "rule_type": "calculation", "title": "Desconto",
        "plain_english": "Se pedido > 500, 10%", "conditions": [],
    }]
    mock_decisions.return_value = []
    mock_env.return_value = "DATABASE_URL: (usada em config.py)"

    mock_llm.stream.return_value = iter([
        {"content": "def calcular_desconto(valor):\n"},
        {"content": "    if valor > 500:\n"},
        {"content": "        return valor * 0.9\n"},
        {"content": "    return valor\n"},
    ])

    with patch("mcp.tools.get_patterns.get_team_patterns", return_value="Naming: snake_case"):
        resp = admin_client.post("/api/codegen/generate", json={
            "description": "Funcao de desconto progressivo",
            "type": "function",
            "repo_name": "test-repo",
        })
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        # Parse SSE events
        events = []
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        # Should have context, token(s), and done events
        types = [e["type"] for e in events]
        assert "context" in types
        assert "token" in types
        assert "done" in types


def test_generate_code_mentions_patterns(admin_client):
    """Generated code references system patterns via mocked context."""
    with patch("app.core.code_generator.search_similar_code_raw", return_value=[]):
        with patch("app.core.code_generator.get_business_rules_raw", return_value=[]):
            with patch("app.core.code_generator.get_architecture_decisions_raw", return_value=[]):
                with patch("app.core.code_generator.get_environment_context", return_value=""):
                    with patch("mcp.tools.get_patterns.get_team_patterns", return_value="Naming: snake_case"):
                        with patch("app.core.code_generator.llm_router") as mock_llm:
                            mock_llm.stream.return_value = iter([
                                {"content": "# Seguindo padrao snake_case do time\ndef calcular(): pass"},
                            ])

                            resp = admin_client.post("/api/codegen/generate", json={
                                "description": "calc",
                                "type": "function",
                                "repo_name": "test-repo",
                            })
                            assert resp.status_code == 200
                            assert "snake_case" in resp.text


def test_generate_code_suporte_forbidden(suporte_client):
    """Suporte cannot generate code."""
    resp = suporte_client.post("/api/codegen/generate", json={
        "description": "test",
        "type": "function",
        "repo_name": "test-repo",
    })
    assert resp.status_code in (401, 403)


def test_generate_code_dev_allowed(dev_client):
    """Dev can generate code."""
    with patch("app.core.code_generator.search_similar_code_raw", return_value=[]):
        with patch("app.core.code_generator.get_business_rules_raw", return_value=[]):
            with patch("app.core.code_generator.get_architecture_decisions_raw", return_value=[]):
                with patch("app.core.code_generator.get_environment_context", return_value=""):
                    with patch("mcp.tools.get_patterns.get_team_patterns", return_value=""):
                        with patch("app.core.code_generator.llm_router") as mock_llm:
                            mock_llm.stream.return_value = iter([{"content": "ok"}])

                            resp = dev_client.post("/api/codegen/generate", json={
                                "description": "test",
                                "type": "function",
                                "repo_name": "test-repo",
                            })
                            assert resp.status_code == 200


# --- GET /api/codegen/history ---

def test_codegen_history(admin_client):
    """History returns paginated list of user's generations."""
    resp = admin_client.get("/api/codegen/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "generations" in data
    assert "total" in data
    assert "page" in data


def test_codegen_history_suporte_forbidden(suporte_client):
    """Suporte cannot access history."""
    resp = suporte_client.get("/api/codegen/history")
    assert resp.status_code in (401, 403)


# --- GET /api/codegen/{id} ---

def test_codegen_detail_not_found(admin_client):
    """GET non-existent generation returns 404."""
    resp = admin_client.get("/api/codegen/nonexistent-id")
    assert resp.status_code == 404


def test_codegen_detail_success(admin_client):
    """GET existing generation returns full detail."""
    gen_row = {
        "id": "gen-001",
        "repo_name": "test-repo",
        "request_description": "Desconto progressivo",
        "request_type": "function",
        "file_path": None,
        "use_context": True,
        "context_used": {"similar_code": [], "business_rules": []},
        "generated_code": "def calc(): pass",
        "explanation": "Seguindo padroes do time",
        "model_used": "gpt-4",
        "tokens_used": 500,
        "cost_usd": 0.01,
        "created_at": "2026-03-06 12:00:00",
    }

    def mock_session():
        session = MagicMock()
        session.execute.return_value.mappings.return_value.first.return_value = gen_row
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.get("/api/codegen/gen-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "gen-001"
    assert data["generated_code"] == "def calc(): pass"
    assert data["explanation"] == "Seguindo padroes do time"
    assert data["context_used"] is not None


# --- Code/explanation split ---

def test_split_code_explanation():
    """Utility splits code and explanation correctly."""
    from app.api.routes.codegen import _split_code_explanation

    content = "def calc():\n    pass\n\nExplicacao:\nSeguindo padroes"
    code, explanation = _split_code_explanation(content)
    assert "def calc" in code
    assert "Seguindo" in explanation


def test_split_code_no_explanation():
    """No explanation marker returns all as code."""
    from app.api.routes.codegen import _split_code_explanation

    content = "def calc():\n    return 42"
    code, explanation = _split_code_explanation(content)
    assert code == "def calc():\n    return 42"
    assert explanation == ""
