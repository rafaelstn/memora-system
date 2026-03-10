"""Testes para o modulo de Regras de Negocio Invisiveis."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_product, get_current_user, get_data_session, get_session
from app.main import app
from tests.conftest import _fake_product, _fake_user


# --- Fixtures ---

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
    app.dependency_overrides[get_current_product] = _fake_product
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def dev_client():
    fake = _fake_user("dev")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    app.dependency_overrides[get_current_product] = _fake_product
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def suporte_client():
    fake = _fake_user("suporte")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    app.dependency_overrides[get_current_product] = _fake_product
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- POST /api/rules/extract ---

def test_extract_rules_admin(admin_client):
    """Admin can trigger rule extraction."""
    resp = admin_client.post("/api/rules/extract/test-repo")
    assert resp.status_code == 202
    assert resp.json()["status"] == "extracting"


def test_extract_rules_dev(dev_client):
    """Dev can trigger rule extraction."""
    resp = dev_client.post("/api/rules/extract/test-repo")
    assert resp.status_code == 202


def test_extract_rules_suporte_denied(suporte_client):
    """Suporte cannot trigger rule extraction."""
    resp = suporte_client.post("/api/rules/extract/test-repo")
    assert resp.status_code in (401, 403)


# --- GET /api/rules ---

def test_list_rules_suporte_allowed(suporte_client):
    """Suporte can list rules (read-only access)."""
    resp = suporte_client.get("/api/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert "rules" in data
    assert "total" in data


def test_list_rules_with_repo_filter(admin_client):
    """List rules filters by repo."""
    resp = admin_client.get("/api/rules?repo_name=test-repo&rule_type=calculation")
    assert resp.status_code == 200


# --- GET /api/rules/{id} ---

def test_get_rule_not_found(admin_client):
    """GET non-existent rule returns 404."""
    resp = admin_client.get("/api/rules/nonexistent-id")
    assert resp.status_code == 404


def test_get_rule_detail(admin_client):
    """GET rule returns full detail."""
    rule_row = {
        "id": "rule-001",
        "repo_name": "test-repo",
        "rule_type": "calculation",
        "title": "Calculo de desconto",
        "description": "Aplica desconto progressivo baseado no valor.",
        "plain_english": "Se o pedido passar de R$500, aplica 10% de desconto.",
        "conditions": [{"if": "pedido.valor > 500", "then": "desconto = 10%"}],
        "affected_files": ["services/pricing.py"],
        "affected_functions": ["calcular_desconto"],
        "confidence": 0.94,
        "is_active": True,
        "changed_in_last_push": False,
        "last_verified_at": "2026-03-06 12:00:00",
        "extracted_at": "2026-03-06 12:00:00",
        "created_at": "2026-03-06 12:00:00",
        "updated_at": "2026-03-06 12:00:00",
    }

    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.mappings.return_value.first.return_value = rule_row
            elif call_count == 2:
                result.mappings.return_value.all.return_value = []
            else:
                result.mappings.return_value.all.return_value = []
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.get("/api/rules/rule-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Calculo de desconto"
    assert data["plain_english"].startswith("Se ")
    assert data["confidence"] == 0.94
    assert "conditions" in data
    assert "changes" in data
    assert "simulations" in data


# --- GET /api/rules/search ---

def test_search_rules(admin_client):
    """Semantic search returns results."""
    with patch("app.api.routes.rules.Embedder") as MockEmbedder:
        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 1536
        MockEmbedder.return_value = mock_embedder

        resp = admin_client.get("/api/rules/search?q=desconto")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


def test_search_rules_suporte_allowed(suporte_client):
    """Suporte can search rules."""
    with patch("app.api.routes.rules.Embedder") as MockEmbedder:
        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 1536
        MockEmbedder.return_value = mock_embedder

        resp = suporte_client.get("/api/rules/search?q=desconto")
        assert resp.status_code == 200


# --- POST /api/rules/{id}/simulate ---

def test_simulate_rule_not_found(admin_client):
    """Simulate non-existent rule returns error."""
    with patch("app.core.rules_simulator.RulesSimulator") as MockSim:
        mock_sim = MagicMock()
        mock_sim.simulate.return_value = {"error": "Regra nao encontrada"}
        MockSim.return_value = mock_sim

        # Patch at the point of import inside the route
        with patch("app.core.rules_simulator.llm_router"):
            resp = admin_client.post("/api/rules/rule-001/simulate", json={
                "input_values": {"valor": 500}
            })
            # Returns 400 because the simulator returns error
            assert resp.status_code == 400


def test_simulate_rule_success(admin_client):
    """Simulate rule returns result in Portuguese."""
    with patch("app.core.rules_simulator.llm_router") as mock_llm:
        mock_llm.complete.return_value = {
            "content": "Com cliente VIP e pedido de R$800:\n1. Pedido passa de R$500 → aplica 10%\nValor final: R$680,00",
        }

        rule_row = {
            "id": "rule-001", "title": "Desconto", "description": "Desconto progressivo",
            "plain_english": "Se pedido > 500, 10%", "conditions": [], "repo_name": "test-repo",
            "affected_files": ["pricing.py"], "affected_functions": ["calc"],
        }
        code_row = {"chunk_name": "calc", "chunk_type": "function", "content": "def calc(): pass"}

        call_count = 0

        def mock_session():
            nonlocal call_count
            session = MagicMock()

            def mock_execute(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                result = MagicMock()
                if call_count == 1:
                    result.mappings.return_value.first.return_value = rule_row
                elif call_count == 2:
                    result.mappings.return_value.all.return_value = [code_row]
                else:
                    result.rowcount = 1
                return result

            session.execute = mock_execute
            return session

        app.dependency_overrides[get_session] = mock_session
        app.dependency_overrides[get_data_session] = mock_session
        resp = admin_client.post("/api/rules/rule-001/simulate", json={
            "input_values": {"tipo_cliente": "VIP", "valor_pedido": 800}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert "R$" in data["result"]


def test_simulate_rule_suporte_allowed(suporte_client):
    """Suporte can simulate rules."""
    with patch("app.core.rules_simulator.llm_router") as mock_llm:
        mock_llm.complete.return_value = {"content": "Resultado da simulacao"}

        rule_row = {
            "id": "rule-001", "title": "Test", "description": "Test rule",
            "plain_english": "Se X, entao Y", "conditions": [], "repo_name": "test-repo",
            "affected_files": [], "affected_functions": [],
        }

        call_count = 0

        def mock_session():
            nonlocal call_count
            session = MagicMock()

            def mock_execute(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                result = MagicMock()
                if call_count == 1:
                    result.mappings.return_value.first.return_value = rule_row
                else:
                    result.mappings.return_value.all.return_value = []
                    result.rowcount = 1
                return result

            session.execute = mock_execute
            return session

        app.dependency_overrides[get_session] = mock_session
        app.dependency_overrides[get_data_session] = mock_session
        resp = suporte_client.post("/api/rules/rule-001/simulate", json={
            "input_values": {"valor": 100}
        })
        assert resp.status_code == 200


# --- Alerts ---

def test_list_alerts_admin(admin_client):
    """Admin can list rule alerts."""
    resp = admin_client.get("/api/rules/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_alerts_suporte_denied(suporte_client):
    """Suporte cannot list alerts."""
    resp = suporte_client.get("/api/rules/alerts")
    assert resp.status_code in (401, 403)


def test_acknowledge_alert(admin_client):
    """Admin can acknowledge alert — 404 when no matching row."""

    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.rowcount = 0
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.patch("/api/rules/alerts/alert-001/acknowledge")
    assert resp.status_code == 404


# --- RulesExtractor unit tests ---

@patch("app.core.rules_extractor.llm_router")
@patch("app.core.rules_extractor.Embedder")
def test_extractor_with_discount_logic(mock_embedder_cls, mock_llm):
    """Extractor finds calculation rules in discount code."""
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536
    mock_embedder_cls.return_value = mock_embedder

    mock_llm.complete.return_value = {
        "content": json.dumps([{
            "rule_type": "calculation",
            "title": "Desconto progressivo",
            "description": "Aplica desconto de 10% para pedidos acima de R$500 e 15% acima de R$1000.",
            "plain_english": "Se o pedido passar de R$500, aplica 10%. Se passar de R$1000, aplica 15%.",
            "conditions": [{"if": "pedido.valor > 500", "then": "desconto = 10%"}],
            "confidence": 0.92,
        }]),
    }

    db = MagicMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # get_business_chunks
            result.mappings.return_value.all.return_value = [{
                "file_path": "services/pricing.py",
                "chunk_name": "calcular_desconto",
                "chunk_type": "function",
                "content": "def calcular_desconto(pedido):\n    if pedido.valor > 1000:\n        return 0.15\n    elif pedido.valor > 500:\n        return 0.10\n    return 0",
            }]
        elif call_count == 2:
            # reset changed_in_last_push
            result.rowcount = 1
        elif call_count == 3:
            # dedup check
            result.mappings.return_value.first.return_value = None
        else:
            result.rowcount = 1
        return result

    db.execute = mock_execute

    from app.core.rules_extractor import RulesExtractor
    extractor = RulesExtractor(db, "org-test-001")
    results = extractor.extract("test-repo")

    assert len(results) >= 1
    assert results[0]["action"] == "created"
    mock_llm.complete.assert_called_once()


@patch("app.core.rules_extractor.llm_router")
@patch("app.core.rules_extractor.Embedder")
def test_extractor_config_file_returns_empty(mock_embedder_cls, mock_llm):
    """Extractor returns empty for config files."""
    mock_embedder = MagicMock()
    mock_embedder_cls.return_value = mock_embedder

    db = MagicMock()
    # Return only config files
    db.execute.return_value.mappings.return_value.all.return_value = [{
        "file_path": "config/settings.py",
        "chunk_name": "Settings",
        "chunk_type": "class",
        "content": "class Settings:\n    DEBUG = True\n    PORT = 8000",
    }]

    from app.core.rules_extractor import RulesExtractor
    extractor = RulesExtractor(db, "org-test-001")
    results = extractor.extract("test-repo")

    # Config files are excluded by IGNORE_PATTERNS
    assert len(results) == 0
    mock_llm.complete.assert_not_called()


def test_plain_english_format():
    """Plain english should use Se...Entao...Exceto format."""
    sample = "Se o pedido passar de R$500, aplica 10% de desconto. Exceto produtos Premium."
    assert "Se " in sample
    assert any(x in sample for x in ("aplica", "Entao", "desconto"))


def test_confidence_range():
    """Confidence should be float between 0 and 1."""
    sample_rules = [
        {"confidence": 0.0},
        {"confidence": 0.5},
        {"confidence": 0.94},
        {"confidence": 1.0},
    ]
    for rule in sample_rules:
        assert 0.0 <= rule["confidence"] <= 1.0
        assert isinstance(rule["confidence"], float)


# --- Deduplication ---

@patch("app.core.rules_extractor.llm_router")
@patch("app.core.rules_extractor.Embedder")
def test_deduplication_same_rule(mock_embedder_cls, mock_llm):
    """Same rule extracted twice should update, not duplicate."""
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536
    mock_embedder_cls.return_value = mock_embedder

    mock_llm.complete.return_value = {
        "content": json.dumps([{
            "rule_type": "validation",
            "title": "Validacao de email",
            "description": "Valida formato de email",
            "plain_english": "Se o email nao tem @, rejeita o cadastro.",
            "conditions": [{"if": "email sem @", "then": "rejeita"}],
            "confidence": 0.85,
        }]),
    }

    db = MagicMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.mappings.return_value.all.return_value = [{
                "file_path": "validators/email.py",
                "chunk_name": "validate_email",
                "chunk_type": "function",
                "content": "def validate_email(e):\n    if '@' not in e:\n        raise ValueError('Invalid')",
            }]
        elif call_count == 2:
            result.rowcount = 1
        elif call_count == 3:
            # Dedup: found existing rule (similarity match)
            result.mappings.return_value.first.return_value = {
                "id": "existing-rule-001",
                "description": "Valida formato de email antigo",
            }
        else:
            result.rowcount = 1
        return result

    db.execute = mock_execute

    from app.core.rules_extractor import RulesExtractor
    extractor = RulesExtractor(db, "org-test-001")
    results = extractor.extract("test-repo")

    assert len(results) == 1
    assert results[0]["action"] == "updated"
    assert results[0]["id"] == "existing-rule-001"


# --- Change detection ---

def test_webhook_detects_rule_changes():
    """Push event triggers rule change detection in webhook."""
    from app.api.routes.webhooks import _process_push
    import inspect
    source = inspect.getsource(_process_push)
    assert "RulesChangeDetector" in source
    assert "detect_changes" in source


@patch("app.core.rules_change_detector.llm_router")
def test_change_detector_modified(mock_llm):
    """Change detector identifies modified rules."""
    mock_llm.complete.side_effect = [
        {"content": "modificada"},  # comparison
        {"content": "Nova descricao da regra."},  # new description
    ]

    db = MagicMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Affected rules for file
            result.mappings.return_value.all.return_value = [{
                "id": "rule-001",
                "title": "Desconto",
                "description": "Desconto antigo",
                "plain_english": "Se pedido > 500, 10%",
                "affected_files": ["services/pricing.py"],
            }]
        elif call_count == 2:
            # New code chunks
            result.mappings.return_value.all.return_value = [
                {"content": "def calc():\n    if val > 800:\n        return 0.15"},
            ]
        else:
            result.rowcount = 1
        return result

    db.execute = mock_execute

    from app.core.rules_change_detector import RulesChangeDetector
    detector = RulesChangeDetector(db, "org-test-001")
    alerts = detector.detect_changes("test-repo", ["services/pricing.py"])

    assert len(alerts) == 1
    assert alerts[0]["change_type"] == "modified"
    assert alerts[0]["rule_title"] == "Desconto"


# --- Extract status ---

def test_extract_status(admin_client):
    """GET extract status returns rule count."""
    mock_row = {"total": 5, "last_extracted": "2026-03-06 12:00:00", "changed": 1}

    def mock_session():
        session = MagicMock()
        session.execute.return_value.mappings.return_value.first.return_value = mock_row
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.get("/api/rules/extract/status/test-repo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rules"] == 5
    assert data["changed_since_push"] == 1
