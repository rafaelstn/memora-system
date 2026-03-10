"""Testes do Modulo 3 — Memoria Tecnica (knowledge extraction, ADRs, search, documents, wiki, timeline)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# --- Helpers ---


def _mock_knowledge_db():
    """Mock DB with knowledge-specific defaults."""
    db = MagicMock()
    # Default: no rows returned
    db.execute.return_value.mappings.return_value.all.return_value = []
    db.execute.return_value.mappings.return_value.first.return_value = None
    db.execute.return_value.first.return_value = None
    db.execute.return_value.scalar.return_value = 0
    db.execute.return_value.rowcount = 1
    return db


# --- POST /api/knowledge/adrs ---


def test_create_adr(admin_client):
    """POST /api/knowledge/adrs creates an ADR entry."""
    with patch("app.api.routes.knowledge.Embedder") as MockEmbedder:
        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 1536
        MockEmbedder.return_value = mock_embedder

        resp = admin_client.post("/api/knowledge/adrs", json={
            "title": "Migrar para pgvector",
            "content": "## Contexto\nPrecisamos de busca semantica.\n## Decisao\nUsar pgvector.",
            "decision_type": "arquitetura",
            "file_paths": ["app/core/search.py"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["title"] == "Migrar para pgvector"


def test_create_adr_missing_title(admin_client):
    """POST /api/knowledge/adrs without title fails validation."""
    resp = admin_client.post("/api/knowledge/adrs", json={
        "content": "Algum conteudo",
    })
    # Pydantic should require title
    assert resp.status_code == 422


def test_create_adr_suporte_forbidden(suporte_client):
    """POST /api/knowledge/adrs forbidden for suporte role."""
    resp = suporte_client.post("/api/knowledge/adrs", json={
        "title": "Teste",
        "content": "Conteudo",
    })
    assert resp.status_code == 403


# --- DELETE /api/knowledge/adrs ---


def test_delete_adr(admin_client):
    """DELETE /api/knowledge/adrs/{id} removes the entry."""
    resp = admin_client.delete("/api/knowledge/adrs/adr-test-001")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_delete_adr_not_found(admin_client):
    """DELETE /api/knowledge/adrs/{id} returns 404 if not found."""
    from app.api.deps import get_data_session, get_session
    db = _mock_knowledge_db()
    db.execute.return_value.rowcount = 0
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_data_session] = lambda: db
    try:
        resp = admin_client.delete("/api/knowledge/adrs/nonexistent")
        assert resp.status_code == 404
    finally:
        from tests.conftest import _mock_session
        app.dependency_overrides[get_session] = _mock_session
        app.dependency_overrides[get_data_session] = _mock_session


# --- GET /api/knowledge/search ---


def test_search_knowledge(admin_client):
    """GET /api/knowledge/search returns results."""
    with patch("app.api.routes.knowledge.Embedder") as MockEmbedder:
        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 1536
        MockEmbedder.return_value = mock_embedder

        resp = admin_client.get("/api/knowledge/search?q=pgvector")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


def test_search_knowledge_short_query(admin_client):
    """GET /api/knowledge/search with short query fails."""
    resp = admin_client.get("/api/knowledge/search?q=a")
    assert resp.status_code == 422


# --- GET /api/knowledge/entries ---


def test_list_entries(admin_client):
    """GET /api/knowledge/entries returns list."""
    resp = admin_client.get("/api/knowledge/entries")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_entries_with_filters(admin_client):
    """GET /api/knowledge/entries with source_type filter."""
    resp = admin_client.get("/api/knowledge/entries?source_type=pr")
    assert resp.status_code == 200


# --- GET /api/knowledge/timeline ---


def test_timeline(admin_client):
    """GET /api/knowledge/timeline returns entries."""
    resp = admin_client.get("/api/knowledge/timeline")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_timeline_with_file_path(admin_client):
    """GET /api/knowledge/timeline?file_path=... filters by file."""
    resp = admin_client.get("/api/knowledge/timeline?file_path=app/core/auth.py")
    assert resp.status_code == 200


# --- POST /api/knowledge/documents ---


def test_upload_document_invalid_type(admin_client):
    """POST /api/knowledge/documents rejects unsupported file types."""
    import io
    resp = admin_client.post(
        "/api/knowledge/documents",
        files={"file": ("test.exe", io.BytesIO(b"malicious"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "suportado" in resp.json()["detail"].lower() or "Aceitos" in resp.json()["detail"]


def test_upload_document_valid(admin_client):
    """POST /api/knowledge/documents accepts .txt file."""
    import io
    with patch("app.api.routes.knowledge.get_upload_path", return_value="/tmp/test_doc.txt"):
        with patch("builtins.open", create=True):
            resp = admin_client.post(
                "/api/knowledge/documents",
                files={"file": ("readme.txt", io.BytesIO(b"Hello World"), "text/plain")},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "processing"
            assert "document_id" in data


# --- GET /api/knowledge/documents ---


def test_list_documents(admin_client):
    """GET /api/knowledge/documents returns list."""
    resp = admin_client.get("/api/knowledge/documents")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# --- GET /api/knowledge/stats ---


def test_knowledge_stats(admin_client):
    """GET /api/knowledge/stats returns counts."""
    resp = admin_client.get("/api/knowledge/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_entries" in data
    assert "prs_commits" in data
    assert "documents" in data
    assert "adrs" in data
    assert "wikis" in data


# --- Wiki endpoints ---


def test_list_wikis(admin_client):
    """GET /api/knowledge/wikis returns list."""
    resp = admin_client.get("/api/knowledge/wikis")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_generate_wiki(admin_client):
    """POST /api/knowledge/wiki/generate starts generation."""
    resp = admin_client.post("/api/knowledge/wiki/generate", json={
        "repo_id": "repo-001",
        "component_path": "app/core/auth.py",
        "component_name": "Auth",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "generating"


# --- Sync endpoint ---


def test_sync_repo(admin_client):
    """POST /api/knowledge/sync/{repo} starts sync."""
    resp = admin_client.post("/api/knowledge/sync/owner/repo")
    assert resp.status_code == 200
    assert resp.json()["status"] == "syncing"


# --- Knowledge Extractor unit tests ---


def test_parse_extraction_response_valid_json():
    """_parse_extraction_response handles valid JSON."""
    from app.core.knowledge_extractor import _parse_extraction_response

    response = json.dumps({
        "title": "Implementar busca hibrida",
        "summary": "Combinamos busca semantica com BM25.",
        "decision_type": "arquitetura",
        "components": ["app/core/search.py"],
        "reasoning": "Melhora a qualidade dos resultados.",
    })
    result = _parse_extraction_response(response)
    assert result["title"] == "Implementar busca hibrida"
    assert result["decision_type"] == "arquitetura"
    assert "search.py" in result["components"][0]


def test_parse_extraction_response_markdown_wrapped():
    """_parse_extraction_response handles markdown code blocks."""
    from app.core.knowledge_extractor import _parse_extraction_response

    response = '```json\n{"title": "Teste", "summary": "Resumo", "decision_type": "padrao", "components": [], "reasoning": ""}\n```'
    result = _parse_extraction_response(response)
    assert result["title"] == "Teste"


def test_parse_extraction_response_malformed():
    """_parse_extraction_response falls back on malformed JSON."""
    from app.core.knowledge_extractor import _parse_extraction_response

    result = _parse_extraction_response("This is not JSON at all")
    assert result["title"] == "This is not JSON at all"[:80]
    assert result["decision_type"] == "correcao"


# --- Document Processor unit tests ---


def test_extract_text_plain():
    """extract_text handles plain text files."""
    import tempfile
    import os
    from app.core.document_processor import extract_text

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Conteudo do documento de teste.")
        f.flush()
        path = f.name

    try:
        text = extract_text(path, "txt")
        assert "Conteudo do documento" in text
    finally:
        os.unlink(path)


def test_extract_text_md():
    """extract_text handles markdown files."""
    import tempfile
    import os
    from app.core.document_processor import extract_text

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Titulo\n\nConteudo markdown.")
        f.flush()
        path = f.name

    try:
        text = extract_text(path, "md")
        assert "Titulo" in text
        assert "Conteudo markdown" in text
    finally:
        os.unlink(path)


# --- Wiki Generator section validation ---


def test_wiki_sections_in_prompt():
    """Wiki generator prompt includes all 6 required sections."""
    from app.core.wiki_generator import WIKI_USER_TEMPLATE

    required_sections = [
        "O que e",
        "Como funciona",
        "Decisoes de arquitetura",
        "Historico de mudancas relevantes",
        "Como modificar com seguranca",
        "Armadilhas conhecidas",
    ]
    for section in required_sections:
        assert section in WIKI_USER_TEMPLATE, f"Missing section: {section}"
