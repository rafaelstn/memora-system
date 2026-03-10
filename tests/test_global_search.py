"""Testes da busca global."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ── Backend: global_search() ──────────────────────────────


@patch("app.core.global_search.Embedder")
def test_global_search_returns_grouped_results(mock_embedder_cls):
    """Busca retorna resultados de multiplas fontes simultaneamente."""
    from app.core.global_search import global_search

    mock_embedder_cls.return_value.embed_text.return_value = [0.1] * 1536

    mock_db = MagicMock()
    # Conversations: 1 result
    row_conv = MagicMock()
    row_conv.id = "msg-001"
    row_conv.title = "Conversa sobre desconto"
    row_conv.content = "Como funciona o desconto por volume?"
    row_conv.created_at = MagicMock(isoformat=lambda: "2026-03-01T10:00:00")
    row_conv.repo_name = "my-repo"
    row_conv.conv_id = "conv-001"

    # Error alert: 1 result
    row_alert = MagicMock()
    row_alert.id = "alert-001"
    row_alert.title = "Erro no calculo de desconto"
    row_alert.explanation = "NullPointerException no modulo de pricing"
    row_alert.severity = "high"
    row_alert.project_id = "proj-001"
    row_alert.created_at = MagicMock(isoformat=lambda: "2026-03-02T10:00:00")

    call_count = {"n": 0}

    def execute_side(*args, **kwargs):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.fetchall.return_value = [row_conv]
        elif call_count["n"] == 7:  # error_alerts is 6th search (index 6)
            result.fetchall.return_value = [row_alert]
        else:
            result.fetchall.return_value = []
        return result

    mock_db.execute.side_effect = execute_side

    data = global_search(mock_db, "desconto", "org-001", "prod-001", "admin", limit=3)

    assert "results" in data
    assert data["total"] > 0
    assert data["query"] == "desconto"


@patch("app.core.global_search.Embedder")
def test_global_search_security_hidden_from_suporte(mock_embedder_cls):
    """Usuario suporte nao recebe findings de seguranca."""
    from app.core.global_search import global_search

    mock_embedder_cls.return_value.embed_text.return_value = [0.1] * 1536

    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []

    data = global_search(mock_db, "vulnerabilidade", "org-001", "prod-001", "suporte", limit=3)

    # security_findings should not be in results even if empty
    assert "security_findings" not in data["results"]


@patch("app.core.global_search.Embedder")
def test_global_search_source_failure_doesnt_break(mock_embedder_cls):
    """Timeout/erro por fonte nao derruba a busca inteira."""
    from app.core.global_search import global_search

    mock_embedder_cls.return_value.embed_text.return_value = [0.1] * 1536

    mock_db = MagicMock()

    call_count = {"n": 0}

    def execute_side(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("DB timeout")
        result = MagicMock()
        result.fetchall.return_value = []
        return result

    mock_db.execute.side_effect = execute_side

    # Should not raise
    data = global_search(mock_db, "teste", "org-001", "prod-001", "admin", limit=3)
    assert isinstance(data["results"], dict)


# ── Rota GET /api/search/global ──────────────────────────────


@patch("app.core.global_search.global_search")
def test_search_route_success(mock_search, admin_client):
    """Rota retorna resultados corretamente."""
    mock_search.return_value = {
        "results": {"conversations": [{"id": "1", "title": "Test"}]},
        "total": 1,
        "query": "test",
    }
    response = admin_client.get("/api/search/global?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


def test_search_route_empty_query(admin_client):
    """Busca vazia retorna 422 (validation error)."""
    response = admin_client.get("/api/search/global?q=")
    assert response.status_code == 422


def test_search_route_long_query(admin_client):
    """Query muito longa retorna 422."""
    long_q = "a" * 501
    response = admin_client.get(f"/api/search/global?q={long_q}")
    assert response.status_code == 422


@patch("app.core.global_search.global_search")
def test_search_route_works_for_suporte(mock_search, suporte_client):
    """Suporte pode usar a busca global."""
    mock_search.return_value = {"results": {}, "total": 0, "query": "test"}
    response = suporte_client.get("/api/search/global?q=test")
    assert response.status_code == 200


@patch("app.core.global_search.global_search")
def test_search_route_respects_limit(mock_search, admin_client):
    """Parametro limit e passado corretamente."""
    mock_search.return_value = {"results": {}, "total": 0, "query": "test"}
    admin_client.get("/api/search/global?q=test&limit=3")
    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args
    assert call_kwargs[1]["limit"] == 3 or call_kwargs[0][5] == 3


# ── Helpers ──────────────────────────────


def test_truncate_function():
    """_truncate corta strings longas."""
    from app.core.global_search import _truncate

    assert _truncate(None) == ""
    assert _truncate("short") == "short"
    assert len(_truncate("x" * 200)) == 153  # 150 + "..."
    assert _truncate("line1\nline2") == "line1 line2"
