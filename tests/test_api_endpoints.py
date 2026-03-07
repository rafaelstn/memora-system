"""Testes dos endpoints da API — verifica que rotas existem e respondem corretamente."""
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Health endpoint retorna status ok (não requer auth)."""
    with patch("app.main.engine") as mock_engine:
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = lambda s, *a: None
        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert data["version"] == "0.2.0"


def test_ask_endpoint_requires_auth():
    """POST /api/ask sem auth retorna 403."""
    response = client.post("/api/ask", json={"question": "test", "repo_name": "test"})
    assert response.status_code == 401


def test_ingest_endpoint_requires_auth():
    """POST /api/ingest sem auth retorna 403."""
    response = client.post("/api/ingest", json={"repo_path": "/app"})
    assert response.status_code == 401


def test_conversations_requires_auth():
    """GET /conversations sem auth retorna 403."""
    response = client.get("/api/conversations?repo_name=test")
    assert response.status_code == 401


@patch("app.api.routes.ask.ask_assistant")
def test_ask_returns_answer_and_sources(mock_ask, admin_client):
    """POST /api/ask com auth e dados válidos retorna answer e sources."""
    mock_ask.return_value = {
        "answer": "Resposta de teste",
        "sources": [{"file": "app/main.py", "chunk_name": "health", "content_preview": "..."}],
    }

    response = admin_client.post(
        "/api/ask",
        json={"question": "O que faz o health?", "repo_name": "memora"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) >= 1


@patch("app.api.routes.ingest.ingest_repository")
def test_ingest_returns_result(mock_ingest, admin_client):
    """POST /api/ingest com auth retorna repo_name, files_processed, chunks_created."""
    mock_ingest.return_value = {
        "repo_name": "memora",
        "files_processed": 10,
        "chunks_created": 42,
    }

    response = admin_client.post(
        "/api/ingest",
        json={"repo_path": "/app", "repo_name": "memora"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["repo_name"] == "memora"
    assert data["files_processed"] == 10
    assert data["chunks_created"] == 42
