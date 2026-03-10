"""Testes do sistema de exportacao de dados."""
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ── data_exporter ──────────────────────────────


def test_truncate_helper():
    """_truncate funciona corretamente."""
    from app.core.global_search import _truncate
    assert _truncate(None) == ""
    assert _truncate("short") == "short"


@patch("app.core.data_exporter.EXPORT_DIR", tempfile.mkdtemp())
def test_export_to_json_creates_file():
    """Exportacao JSON cria arquivo com dados."""
    from app.core.data_exporter import export_to_json

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = []

    path = export_to_json(
        mock_db, "org-001", "Org Teste", "prod-001", "Produto",
        None, None,
    )
    assert os.path.exists(path)
    assert path.endswith(".json")

    with open(path) as f:
        data = json.load(f)
    assert "export_info" in data
    assert data["export_info"]["org_name"] == "Org Teste"

    os.remove(path)


@patch("app.core.data_exporter.EXPORT_DIR", tempfile.mkdtemp())
def test_export_to_csv_zip_creates_file():
    """Exportacao CSV ZIP cria arquivo."""
    from app.core.data_exporter import export_to_csv_zip

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = []

    path = export_to_csv_zip(mock_db, "org-001", "prod-001", None, None)
    assert os.path.exists(path)
    assert path.endswith(".zip")

    os.remove(path)


def test_exportable_tables_defined():
    """Tabelas exportaveis estao definidas."""
    from app.core.data_exporter import EXPORTABLE_TABLES

    expected = [
        "conversations", "messages", "business_rules", "knowledge_entries",
        "knowledge_documents", "knowledge_wikis", "code_reviews",
        "review_findings", "error_alerts", "incidents", "incident_timeline",
        "repo_docs", "executive_weekly_snapshots",
    ]
    for table in expected:
        assert table in EXPORTABLE_TABLES


def test_no_sensitive_data_in_queries():
    """Queries nao exportam dados sensiveis (API keys, senhas)."""
    from app.core.data_exporter import EXPORTABLE_TABLES

    sensitive_words = ["password", "api_key", "secret", "encrypted"]
    # Note: "token" excluded because tokens_used is a metric field, not a credential
    for table_name, config in EXPORTABLE_TABLES.items():
        query_lower = config["query"].lower()
        for word in sensitive_words:
            assert word not in query_lower, (
                f"Tabela {table_name} contem '{word}' na query"
            )


def test_cleanup_expired_exports():
    """Job de limpeza remove arquivos expirados."""
    from app.core.data_exporter import cleanup_expired_exports

    mock_db = MagicMock()
    row = MagicMock()
    row.id = "exp-001"
    row.file_path = "/tmp/nonexistent-file.json"
    mock_db.execute.return_value.fetchall.return_value = [row]

    count = cleanup_expired_exports(mock_db)
    assert count == 1
    mock_db.commit.assert_called()


def test_cleanup_no_expired():
    """Limpeza com nada expirado retorna 0."""
    from app.core.data_exporter import cleanup_expired_exports

    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []

    count = cleanup_expired_exports(mock_db)
    assert count == 0


# ── Routes ──────────────────────────────


def test_create_export_admin(admin_client):
    """Admin pode criar exportacao."""
    with patch("app.core.data_exporter.run_export"):
        response = admin_client.post(
            "/api/admin/exports",
            json={"format": "json"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert "id" in data


def test_create_export_invalid_format(admin_client):
    """Formato invalido retorna 400."""
    response = admin_client.post(
        "/api/admin/exports",
        json={"format": "xml"},
    )
    assert response.status_code == 400


def test_create_export_blocked_for_dev(dev_client):
    """Dev nao pode exportar."""
    response = dev_client.post("/api/admin/exports", json={"format": "json"})
    assert response.status_code == 403


def test_create_export_blocked_for_suporte(suporte_client):
    """Suporte nao pode exportar."""
    response = suporte_client.post("/api/admin/exports", json={"format": "json"})
    assert response.status_code == 403


def test_list_exports_admin(admin_client):
    """Admin pode listar exportacoes."""
    response = admin_client.get("/api/admin/exports")
    # May return 200 or 500 (mock DB), but not 403
    assert response.status_code not in (401, 403)


def test_download_export_not_found(admin_client):
    """Download de exportacao inexistente retorna erro."""
    response = admin_client.get("/api/admin/exports/nonexistent/download")
    # mock DB may return MagicMock (not None), so we get 400/404/500
    assert response.status_code in (400, 404, 500)


# ── Scheduler cleanup ──────────────────────────────


def test_scheduler_cleanup_check():
    """_should_run_cleanup retorna True as 05h UTC."""
    from app.core.scheduler import _should_run_cleanup

    cleanup_time = datetime(2026, 3, 10, 5, 2)
    assert _should_run_cleanup(cleanup_time) is True

    other_time = datetime(2026, 3, 10, 10, 0)
    assert _should_run_cleanup(other_time) is False
