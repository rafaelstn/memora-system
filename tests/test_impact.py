"""Testes para o modulo de Analise de Impacto de Mudancas."""

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


# --- POST /api/impact/analyze ---

def test_start_analysis(admin_client):
    """Admin can start an impact analysis."""
    resp = admin_client.post("/api/impact/analyze", json={
        "change_description": "Alterar funcao de calculo de desconto",
        "repo_name": "test-repo",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "analysis_id" in data
    assert data["status"] == "analyzing"


def test_start_analysis_with_files(admin_client):
    """Analysis can include affected files."""
    resp = admin_client.post("/api/impact/analyze", json={
        "change_description": "Alterar pricing",
        "repo_name": "test-repo",
        "affected_files": ["services/pricing.py", "tests/test_pricing.py"],
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "analyzing"


def test_start_analysis_dev_allowed(dev_client):
    """Dev can start analysis."""
    resp = dev_client.post("/api/impact/analyze", json={
        "change_description": "test",
        "repo_name": "test-repo",
    })
    assert resp.status_code == 200


def test_start_analysis_suporte_forbidden(suporte_client):
    """Suporte cannot start analysis."""
    resp = suporte_client.post("/api/impact/analyze", json={
        "change_description": "test",
        "repo_name": "test-repo",
    })
    assert resp.status_code in (401, 403)


# --- GET /api/impact/{id} ---

def test_get_analysis_not_found(admin_client):
    """GET nonexistent analysis returns 404."""
    resp = admin_client.get("/api/impact/nonexistent")
    assert resp.status_code == 404


def test_get_analysis_completed(admin_client):
    """GET completed analysis returns findings."""
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
                    "id": "ia-001",
                    "org_id": "org-test-001",
                    "repo_name": "test-repo",
                    "requested_by": "u-test-001",
                    "change_description": "Alterar desconto",
                    "affected_files": ["pricing.py"],
                    "risk_level": "medium",
                    "risk_summary": "Mudanca afeta 2 componentes",
                    "status": "completed",
                    "created_at": "2026-03-06 12:00:00",
                    "updated_at": "2026-03-06 12:05:00",
                }
            else:
                result.mappings.return_value.all.return_value = [{
                    "id": "if-001",
                    "analysis_id": "ia-001",
                    "org_id": "org-test-001",
                    "finding_type": "dependency",
                    "severity": "high",
                    "title": "Modulo de pedidos depende desta funcao",
                    "description": "O modulo orders.py importa calc_discount",
                    "affected_component": "orders",
                    "file_path": "services/orders.py",
                    "recommendation": "Verificar testes de orders apos mudanca",
                    "created_at": "2026-03-06 12:05:00",
                }]
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.get("/api/impact/ia-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "medium"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["finding_type"] == "dependency"


# --- GET /api/impact/history/list ---

def test_list_history(admin_client):
    """History returns user's past analyses."""
    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.mappings.return_value.all.return_value = [{
                    "id": "ia-001",
                    "repo_name": "test-repo",
                    "change_description": "Alterar desconto",
                    "risk_level": "medium",
                    "status": "completed",
                    "created_at": "2026-03-06 12:00:00",
                }]
            else:
                result.mappings.return_value.first.return_value = {"cnt": 1}
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.get("/api/impact/history/list")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["analyses"]) == 1
    assert data["total"] == 1


# --- ImpactAnalyzer ---

@patch("app.core.impact_analyzer.Embedder")
@patch("app.core.impact_analyzer.llm_router")
def test_impact_analyzer_full(mock_llm, mock_embedder_cls):
    """ImpactAnalyzer runs full pipeline and saves findings."""
    from app.core.impact_analyzer import ImpactAnalyzer

    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536
    mock_embedder_cls.return_value = mock_embedder

    # LLM responses
    identify_response = json.dumps({"files": ["pricing.py"], "functions": ["calc_discount"]})
    synthesis_response = json.dumps({
        "risk_level": "high",
        "risk_summary": "Mudanca afeta regra de desconto critica",
        "findings": [
            {
                "type": "business_rule",
                "severity": "high",
                "title": "Regra de desconto progressivo",
                "description": "A regra de desconto > 500 pode ser afetada",
                "recommendation": "Validar com testes",
            },
            {
                "type": "dependency",
                "severity": "medium",
                "title": "orders.py depende de pricing",
                "description": "Modulo de pedidos usa calc_discount",
                "affected_component": "orders",
                "file_path": "services/orders.py",
                "recommendation": "Rodar testes de orders",
            },
        ],
    })

    mock_llm.complete.side_effect = [
        {"content": identify_response},
        {"content": synthesis_response},
    ]

    db = MagicMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Analysis
            result.mappings.return_value.first.return_value = {
                "id": "ia-001",
                "org_id": "org-test-001",
                "change_description": "Alterar funcao de desconto",
                "repo_name": "test-repo",
                "affected_files": None,
            }
        else:
            result.mappings.return_value.all.return_value = []
            result.mappings.return_value.first.return_value = None
            result.rowcount = 1
        return result

    db.execute = mock_execute

    analyzer = ImpactAnalyzer(db, "org-test-001")
    analyzer.analyze("ia-001")

    assert mock_llm.complete.called
    assert db.commit.called


# --- MCP tool ---

@patch("mcp.tools.analyze_impact.Embedder")
@patch("mcp.tools.analyze_impact.llm_router")
def test_mcp_analyze_impact(mock_llm, mock_embedder_cls):
    """MCP tool returns formatted impact report."""
    from mcp.tools.analyze_impact import analyze_change_impact

    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536
    mock_embedder_cls.return_value = mock_embedder

    mock_llm.complete.return_value = {
        "content": json.dumps({
            "risk_level": "medium",
            "summary": "Risco moderado - 2 dependencias afetadas",
            "findings": [
                {"type": "dependency", "title": "orders.py", "description": "Usa calc_discount", "recommendation": "Testar"},
            ],
            "recommendations": ["Rodar testes de integracao"],
        })
    }

    db = MagicMock()
    db.execute.return_value.mappings.return_value.all.return_value = []

    result = analyze_change_impact(db, "org-test-001", "Alterar desconto", "test-repo")
    assert "MEDIO" in result.upper() or "Risco" in result
    assert mock_llm.complete.called
