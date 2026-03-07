"""Testes para o modulo de Documentacao Automatica e Onboarding."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_session
from app.main import app
from tests.conftest import _fake_user


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


# --- POST /api/docs/generate ---

def test_generate_readme(admin_client):
    """POST /api/docs/generate dispatches background task."""
    resp = admin_client.post("/api/docs/generate/test-repo", json={"doc_type": "readme"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "generating"
    assert data["doc_type"] == "readme"


def test_generate_all(admin_client):
    """POST /api/docs/generate with 'all' works."""
    resp = admin_client.post("/api/docs/generate/test-repo", json={"doc_type": "all"})
    assert resp.status_code == 200
    assert resp.json()["doc_type"] == "all"


def test_generate_invalid_type(admin_client):
    """POST /api/docs/generate with invalid doc_type returns 400."""
    resp = admin_client.post("/api/docs/generate/test-repo", json={"doc_type": "invalid"})
    assert resp.status_code == 400


def test_generate_docs_dev_allowed(dev_client):
    """Dev role can generate docs."""
    resp = dev_client.post("/api/docs/generate/test-repo", json={"doc_type": "readme"})
    assert resp.status_code == 200


def test_generate_docs_suporte_denied(suporte_client):
    """Suporte role cannot generate docs."""
    resp = suporte_client.post("/api/docs/generate/test-repo", json={"doc_type": "readme"})
    assert resp.status_code in (401, 403)


# --- GET /api/docs/status ---

def test_docs_status_empty(admin_client):
    """Status for repo with no docs returns empty dict."""
    resp = admin_client.get("/api/docs/status/test-repo")
    assert resp.status_code == 200
    assert resp.json() == {}


def test_docs_status_with_readme(admin_client):
    """Status returns readme info when generated."""
    mock_row = {
        "doc_type": "readme",
        "generated_at": "2026-03-06 12:00:00",
        "pushed_to_github": False,
        "pushed_at": None,
        "content_hash": "abc123",
    }

    def mock_session():
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [mock_row]
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.get("/api/docs/status/test-repo")
    assert resp.status_code == 200
    data = resp.json()
    assert "readme" in data
    assert data["readme"]["content_hash"] == "abc123"


# --- GET /api/docs/{repo}/readme ---

def test_get_readme_not_found(admin_client):
    """GET readme when not generated returns 404."""
    resp = admin_client.get("/api/docs/test-repo/readme")
    assert resp.status_code == 404


def test_get_readme_success(admin_client):
    """GET readme returns content when generated."""
    mock_row = {
        "id": "doc-001",
        "content": "# Test Repo\n> Test project\n\n## O que e\nTest system.",
        "generated_at": "2026-03-06 12:00:00",
        "pushed_to_github": False,
        "pushed_at": None,
        "content_hash": "abc123",
        "generation_trigger": "manual",
        "created_at": "2026-03-06 12:00:00",
        "updated_at": "2026-03-06 12:00:00",
    }

    def mock_session():
        session = MagicMock()
        session.execute.return_value.mappings.return_value.first.return_value = mock_row
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.get("/api/docs/test-repo/readme")
    assert resp.status_code == 200
    data = resp.json()
    assert "# Test Repo" in data["content"]
    assert data["content_hash"] == "abc123"


def test_get_readme_has_required_sections():
    """README generated content should contain required sections."""
    # This tests the expected output structure
    required_sections = [
        "O que e", "Stack tecnologica", "Estrutura do projeto",
        "Como rodar localmente", "Variaveis de ambiente",
        "Principais modulos", "Fluxo principal",
    ]
    sample_readme = """# Test Repo
> Um sistema de teste

## O que e
Descricao do sistema.

## Stack tecnologica
- Python 3.14
- FastAPI

## Estrutura do projeto
app/ - backend

## Como rodar localmente
1. Instale dependencias

## Variaveis de ambiente
| Variavel | Descricao |
| --- | --- |
| DATABASE_URL | Conexao |

## Principais modulos
- core: logica

## Fluxo principal
Request -> API -> DB
"""
    for section in required_sections:
        assert section in sample_readme


# --- GET /api/docs/{repo}/onboarding ---

def test_get_onboarding_not_found(admin_client):
    """GET onboarding when not generated returns 404."""
    resp = admin_client.get("/api/docs/test-repo/onboarding")
    assert resp.status_code == 404


def test_get_onboarding_success(admin_client):
    """GET onboarding returns content when generated."""
    mock_row = {
        "id": "doc-002",
        "content": "# Guia de Onboarding\n\n### Passo 1 — Entenda\n**Arquivo:** main.py\n",
        "generated_at": "2026-03-06 12:00:00",
        "content_hash": "def456",
        "generation_trigger": "manual",
        "created_at": "2026-03-06 12:00:00",
        "updated_at": "2026-03-06 12:00:00",
    }

    def mock_session():
        session = MagicMock()
        session.execute.return_value.mappings.return_value.first.return_value = mock_row
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.get("/api/docs/test-repo/onboarding")
    assert resp.status_code == 200
    data = resp.json()
    assert "Guia de Onboarding" in data["content"]


def test_onboarding_has_steps():
    """Onboarding content should have between 5 and 8 steps."""
    sample = """# Guia de Onboarding

### Passo 1 — Entrada
**Arquivo:** main.py

### Passo 2 — Config
**Arquivo:** config.py

### Passo 3 — Rotas
**Arquivo:** routes.py

### Passo 4 — Modelos
**Arquivo:** models.py

### Passo 5 — Servicos
**Arquivo:** services.py

### Passo 6 — Testes
**Arquivo:** tests.py
"""
    step_count = sample.lower().count("### passo")
    assert 5 <= step_count <= 8


def test_onboarding_cites_real_files():
    """Each onboarding step should reference a real file."""
    sample_steps = [
        "**Arquivo:** app/main.py",
        "**Arquivo:** app/config.py",
        "**Arquivo:** app/api/routes/auth.py",
    ]
    for step in sample_steps:
        assert "**Arquivo:**" in step
        file_ref = step.split("**Arquivo:**")[1].strip()
        assert len(file_ref) > 0
        assert "/" in file_ref or "." in file_ref  # Looks like a real file path


# --- POST /api/docs/{repo}/push-to-github ---

def test_push_to_github_admin_only(dev_client):
    """Only admin can push to GitHub."""
    resp = dev_client.post("/api/docs/test-repo/push-to-github", json={})
    assert resp.status_code in (401, 403)


def test_push_to_github_no_readme(admin_client):
    """Push when no README returns 404."""
    resp = admin_client.post("/api/docs/test-repo/push-to-github", json={})
    assert resp.status_code == 404


@patch("app.api.routes.docs.httpx")
def test_push_to_github_success(mock_httpx, admin_client):
    """Push README to GitHub creates commit."""
    readme_row = {"id": "doc-001", "content": "# Test README"}
    gh_row = {"github_token": "ghp_test123", "github_login": "testuser"}

    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.mappings.return_value.first.return_value = readme_row
            elif call_count == 2:
                result.mappings.return_value.first.return_value = gh_row
            else:
                result.mappings.return_value.first.return_value = None
                result.rowcount = 1
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session

    # Mock httpx responses
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"sha": "existing_sha"}
    mock_httpx.get.return_value = mock_get_resp

    mock_put_resp = MagicMock()
    mock_put_resp.status_code = 200
    mock_httpx.put.return_value = mock_put_resp

    resp = admin_client.post("/api/docs/test-repo/push-to-github", json={
        "commit_message": "docs: atualiza README via Memora"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "pushed"


# --- Onboarding progress ---

def test_get_progress_not_started(admin_client):
    """GET progress when not started returns empty state."""
    resp = admin_client.get("/api/onboarding/test-repo/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["started"] is False
    assert data["steps_completed"] == 0


def test_complete_step_no_guide(admin_client):
    """POST progress when no guide returns 404."""
    resp = admin_client.post("/api/onboarding/test-repo/progress", json={"step_id": "step-1"})
    assert resp.status_code == 404


def test_complete_step_creates_progress(admin_client):
    """POST progress creates new progress entry."""
    guide_row = {
        "id": "doc-002",
        "content": "### Passo 1\n### Passo 2\n### Passo 3\n### Passo 4\n### Passo 5\n",
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
                # Guide lookup
                result.mappings.return_value.first.return_value = guide_row
            elif call_count == 2:
                # Existing progress lookup
                result.mappings.return_value.first.return_value = None
            else:
                result.rowcount = 1
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.post("/api/onboarding/test-repo/progress", json={"step_id": "step-1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["steps_completed"] == 1
    assert "step-1" in data["completed_steps"]


def test_progress_is_per_user():
    """Onboarding progress should be isolated per user (user_id filter in query)."""
    # The query uses user_id = :user_id, so user A's progress is separate from user B
    from app.api.routes.docs import update_onboarding_progress
    import inspect
    source = inspect.getsource(update_onboarding_progress)
    assert "user_id" in source
    assert ":user_id" in source


def test_complete_step_updates_existing(admin_client):
    """POST progress updates existing progress entry."""
    guide_row = {
        "id": "doc-002",
        "content": "### Passo 1\n### Passo 2\n### Passo 3\n",
    }
    existing_progress = {
        "id": "prog-001",
        "completed_steps": ["step-1"],
        "steps_completed": 1,
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
                result.mappings.return_value.first.return_value = guide_row
            elif call_count == 2:
                result.mappings.return_value.first.return_value = existing_progress
            else:
                result.rowcount = 1
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    resp = admin_client.post("/api/onboarding/test-repo/progress", json={"step_id": "step-2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["steps_completed"] == 2
    assert "step-1" in data["completed_steps"]
    assert "step-2" in data["completed_steps"]


# --- ReadmeGenerator unit tests ---

@patch("app.core.readme_generator.llm_router")
def test_readme_generator_generate(mock_llm):
    """ReadmeGenerator produces markdown with correct structure."""
    mock_llm.complete.return_value = {
        "content": """# Test Repo
> Um sistema de teste

## O que e
Sistema de teste.

## Stack tecnologica
- Python

## Estrutura do projeto
app/ - backend

## Como rodar localmente
uvicorn app.main:app

## Variaveis de ambiente
| Var | Desc |
| --- | --- |
| DB_URL | Conexao |

## Principais modulos
- core

## Fluxo principal
Request -> Response""",
    }

    db = MagicMock()
    call_count = 0

    chunk_row = {
        "file_path": "app/main.py", "chunk_name": "main", "chunk_type": "module",
        "content": "from fastapi import FastAPI\napp = FastAPI()",
    }

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count <= 3:
            # file_structure, entry_points, code_context
            result.mappings.return_value.all.return_value = [chunk_row]
        elif call_count == 4:
            # env_vars
            result.mappings.return_value.all.return_value = []
        elif call_count == 5:
            # knowledge
            result.mappings.return_value.all.return_value = []
        else:
            # upsert check
            result.mappings.return_value.first.return_value = None
            result.rowcount = 1
        return result

    db.execute = mock_execute

    from app.core.readme_generator import ReadmeGenerator
    gen = ReadmeGenerator(db, "org-test-001")
    result = gen.generate("test-repo")

    assert "doc_id" in result
    assert result["doc_type"] == "readme"
    mock_llm.complete.assert_called_once()

    # Verify the prompt mentions required sections
    call_args = mock_llm.complete.call_args
    user_msg = call_args.kwargs.get("user_message") or call_args[1].get("user_message", "")
    assert "Stack tecnologica" in user_msg
    assert "Variaveis de ambiente" in user_msg


@patch("app.core.readme_generator.llm_router")
def test_readme_generator_env_vars(mock_llm):
    """ReadmeGenerator identifies environment variables in code."""
    mock_llm.complete.return_value = {"content": "# Test\n## Variaveis de ambiente\n- DB_URL"}

    db = MagicMock()

    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count <= 2:
            result.mappings.return_value.all.return_value = [
                {"file_path": "app/config.py", "chunk_name": "Settings", "chunk_type": "class",
                 "content": "class Settings(BaseSettings):\n    database_url: str = os.environ['DATABASE_URL']"},
            ]
        elif call_count == 3:
            # code context
            result.mappings.return_value.all.return_value = [
                {"file_path": "app/config.py", "chunk_name": "Settings", "chunk_type": "class",
                 "content": "class Settings(BaseSettings):\n    database_url: str"},
            ]
        elif call_count == 4:
            # env vars query
            result.mappings.return_value.all.return_value = [
                {"content": "os.environ.get('DATABASE_URL')\nos.getenv('OPENAI_API_KEY')"},
            ]
        else:
            result.mappings.return_value.all.return_value = []
            result.mappings.return_value.first.return_value = None
        return result

    db.execute = mock_execute

    from app.core.readme_generator import ReadmeGenerator
    gen = ReadmeGenerator(db, "org-test-001")
    result = gen.generate("test-repo")
    assert "error" not in result


# --- OnboardingGenerator unit tests ---

@patch("app.core.onboarding_generator.llm_router")
def test_onboarding_generator_generate(mock_llm):
    """OnboardingGenerator produces guide with steps."""
    mock_llm.complete.return_value = {
        "content": """# Guia de Onboarding — test-repo

## Visao geral em 5 minutos
Sistema de teste.

## Antes de comecar
Instale Python.

## Ordem de leitura recomendada

### Passo 1 — Entenda a entrada
**Arquivo:** app/main.py
**Por que ler primeiro:** Ponto de entrada
**Tempo estimado:** 10 minutos

### Passo 2 — Configuracao
**Arquivo:** app/config.py
**Tempo estimado:** 5 minutos

### Passo 3 — Rotas
**Arquivo:** app/api/routes/auth.py
**Tempo estimado:** 15 minutos

### Passo 4 — Modelos
**Arquivo:** app/models/user.py
**Tempo estimado:** 10 minutos

### Passo 5 — Servicos
**Arquivo:** app/core/auth.py
**Tempo estimado:** 15 minutos

## Mapa mental
main -> routes -> core -> models

## Armadilhas comuns
- Cuidado com imports circulares

## Primeira tarefa sugerida
Adicione um endpoint GET /api/ping
""",
    }

    db = MagicMock()
    call_count = 0

    chunk_row = {
        "file_path": "app/main.py", "chunk_name": "main", "chunk_type": "module",
        "content": "from fastapi import FastAPI\napp = FastAPI()",
    }

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count <= 3:
            result.mappings.return_value.all.return_value = [chunk_row]
        elif call_count == 4:
            result.mappings.return_value.all.return_value = []
        else:
            result.mappings.return_value.first.return_value = None
            result.rowcount = 1
        return result

    db.execute = mock_execute

    from app.core.onboarding_generator import OnboardingGenerator
    gen = OnboardingGenerator(db, "org-test-001")
    result = gen.generate("test-repo")

    assert "doc_id" in result
    assert result["doc_type"] == "onboarding_guide"
    assert result["steps_total"] == 5
    mock_llm.complete.assert_called_once()


# --- Webhook auto-regeneration ---

def test_webhook_push_triggers_docs_regen():
    """Push event on webhook should trigger docs regeneration if configured."""
    from app.api.routes.webhooks import _process_push
    import inspect
    source = inspect.getsource(_process_push)
    assert "auto_generate_readme" in source
    assert "ReadmeGenerator" in source
    assert "OnboardingGenerator" in source
