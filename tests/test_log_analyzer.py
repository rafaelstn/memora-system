"""Testes do LogAnalyzer — analise de logs com IA."""
import json
from unittest.mock import MagicMock, patch

from app.core.log_analyzer import _parse_llm_response, analyze


def test_parse_valid_json():
    """Parse valid JSON response from LLM."""
    raw = json.dumps({
        "title": "Erro de conexao",
        "explanation": "O banco nao respondeu",
        "severity": "high",
        "affected_component": "database",
        "suggested_actions": ["Verificar host", "Reiniciar servico"],
    })
    result = _parse_llm_response(raw)
    assert result["title"] == "Erro de conexao"
    assert result["severity"] == "high"
    assert len(result["suggested_actions"]) == 2


def test_parse_json_with_markdown():
    """Parse JSON wrapped in markdown code block."""
    raw = '```json\n{"title": "Timeout", "explanation": "Timeout na API", "severity": "medium", "affected_component": "api", "suggested_actions": ["Aumentar timeout"]}\n```'
    result = _parse_llm_response(raw)
    assert result["title"] == "Timeout"
    assert result["severity"] == "medium"


def test_parse_malformed_response():
    """Malformed LLM response gets fallback."""
    raw = "Nao consigo analisar este erro, mas parece ser grave."
    result = _parse_llm_response(raw)
    assert result["title"] == "Erro detectado"
    assert result["severity"] == "medium"
    assert raw in result["explanation"]


@patch("app.core.log_analyzer.llm_router")
def test_analyze_database_error(mock_router):
    """Analyze database connection error returns high/critical severity."""
    mock_router.complete.return_value = {
        "content": json.dumps({
            "title": "Falha na conexao com banco de dados",
            "explanation": "O servico nao conseguiu conectar ao PostgreSQL.",
            "severity": "critical",
            "affected_component": "database",
            "suggested_actions": ["Verificar se o DB esta online", "Checar credenciais"],
        })
    }

    mock_db = MagicMock()
    # Mock log entry
    log_data = {
        "id": "log-001",
        "project_id": "proj-001",
        "org_id": "org-001",
        "level": "error",
        "message": "Connection refused: PostgreSQL on port 5432",
        "source": "app/db/connection.py",
        "stack_trace": "Traceback (most recent call last):\n  psycopg2.OperationalError",
        "metadata": None,
    }
    entry_mock = MagicMock()
    entry_mock.__getitem__ = lambda self, key: log_data[key]
    entry_mock.get = lambda key, default=None: log_data.get(key, default)

    call_count = [0]
    def mock_execute(query, params=None):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:  # log entry query
            result.mappings.return_value.first.return_value = entry_mock
        elif call_count[0] == 2:  # recent logs
            result.mappings.return_value.all.return_value = []
        else:  # insert + update
            pass
        return result

    mock_db.execute = mock_execute

    alert_id = analyze(mock_db, "log-001", "org-001")
    assert alert_id is not None
    mock_router.complete.assert_called_once()


@patch("app.core.log_analyzer.llm_router")
def test_analyze_timeout_identifies_component(mock_router):
    """Analyze timeout error identifies affected component."""
    mock_router.complete.return_value = {
        "content": json.dumps({
            "title": "Timeout na API externa",
            "explanation": "A chamada para o servico de pagamento expirou apos 30s.",
            "severity": "high",
            "affected_component": "payment-gateway",
            "suggested_actions": ["Verificar status do gateway"],
        })
    }

    mock_db = MagicMock()
    log_data = {
        "id": "log-002",
        "project_id": "proj-001",
        "org_id": "org-001",
        "level": "error",
        "message": "TimeoutError: Request to payment API timed out after 30000ms",
        "source": "services/payment.py",
        "stack_trace": None,
        "metadata": None,
    }
    entry_mock = MagicMock()
    entry_mock.__getitem__ = lambda self, key: log_data[key]
    entry_mock.get = lambda key, default=None: log_data.get(key, default)

    call_count = [0]
    def mock_execute(query, params=None):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.mappings.return_value.first.return_value = entry_mock
        elif call_count[0] == 2:
            result.mappings.return_value.all.return_value = []
        return result

    mock_db.execute = mock_execute

    alert_id = analyze(mock_db, "log-002", "org-001")
    assert alert_id is not None


@patch("app.core.log_analyzer.llm_router")
def test_analyze_no_stacktrace(mock_router):
    """Analyze log without stack trace still generates useful explanation."""
    mock_router.complete.return_value = {
        "content": json.dumps({
            "title": "Erro de permissao",
            "explanation": "O processo nao tem permissao para acessar o recurso.",
            "severity": "medium",
            "affected_component": "filesystem",
            "suggested_actions": ["Verificar permissoes do diretorio"],
        })
    }

    mock_db = MagicMock()
    log_data = {
        "id": "log-003",
        "project_id": "proj-001",
        "org_id": "org-001",
        "level": "error",
        "message": "PermissionError: /var/data/output.csv",
        "source": None,
        "stack_trace": None,
        "metadata": None,
    }
    entry_mock = MagicMock()
    entry_mock.__getitem__ = lambda self, key: log_data[key]
    entry_mock.get = lambda key, default=None: log_data.get(key, default)

    call_count = [0]
    def mock_execute(query, params=None):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.mappings.return_value.first.return_value = entry_mock
        elif call_count[0] == 2:
            result.mappings.return_value.all.return_value = []
        return result

    mock_db.execute = mock_execute

    alert_id = analyze(mock_db, "log-003", "org-001")
    assert alert_id is not None


@patch("app.core.log_analyzer.llm_router")
def test_analyze_llm_failure_creates_fallback(mock_router):
    """When LLM fails, fallback alert is still created."""
    mock_router.complete.side_effect = Exception("LLM offline")

    mock_db = MagicMock()
    log_data = {
        "id": "log-004",
        "project_id": "proj-001",
        "org_id": "org-001",
        "level": "critical",
        "message": "Out of memory",
        "source": "worker.py",
        "stack_trace": None,
        "metadata": None,
    }
    entry_mock = MagicMock()
    entry_mock.__getitem__ = lambda self, key: log_data[key]
    entry_mock.get = lambda key, default=None: log_data.get(key, default)

    call_count = [0]
    def mock_execute(query, params=None):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.mappings.return_value.first.return_value = entry_mock
        elif call_count[0] == 2:
            result.mappings.return_value.all.return_value = []
        return result

    mock_db.execute = mock_execute

    alert_id = analyze(mock_db, "log-004", "org-001")
    assert alert_id is not None
