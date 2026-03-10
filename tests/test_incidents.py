"""Testes para o modulo de Gestao de Incidentes."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_product, get_current_user, get_data_session, get_session
from app.main import app
from tests.conftest import _fake_product, _fake_user


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


# --- POST /api/incidents (declare) ---

def test_declare_incident(admin_client):
    """Admin can declare an incident."""
    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Alert lookup (title)
                result.mappings.return_value.first.return_value = {
                    "title": "Erro critico no pagamento",
                }
            else:
                result.mappings.return_value.first.return_value = None
                result.mappings.return_value.all.return_value = []
                result.rowcount = 1
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.post("/api/incidents", json={
        "alert_id": "alert-001",
        "project_id": "proj-001",
        "severity": "critical",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["severity"] == "critical"
    assert data["status"] == "open"
    assert "id" in data


def test_declare_incident_with_title(admin_client):
    """Incident can be declared with custom title."""
    resp = admin_client.post("/api/incidents", json={
        "project_id": "proj-001",
        "title": "Incidente manual",
        "severity": "high",
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "Incidente manual"


def test_declare_incident_suporte_forbidden(suporte_client):
    """Suporte cannot declare incidents."""
    resp = suporte_client.post("/api/incidents", json={
        "project_id": "proj-001",
        "title": "test",
        "severity": "high",
    })
    assert resp.status_code in (401, 403)


def test_declare_incident_invalid_severity(admin_client):
    """Invalid severity returns 400."""
    resp = admin_client.post("/api/incidents", json={
        "project_id": "proj-001",
        "title": "test",
        "severity": "mega",
    })
    assert resp.status_code == 400


# --- GET /api/incidents ---

def test_list_incidents(admin_client):
    """List incidents returns paginated results."""
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
                    "id": "inc-001",
                    "title": "Incidente teste",
                    "severity": "high",
                    "status": "open",
                    "project_name": "Test Project",
                    "declared_by_name": "Test User",
                    "declared_at": "2026-03-06 12:00:00",
                    "org_id": "org-test-001",
                    "project_id": "proj-001",
                    "alert_id": None,
                    "description": None,
                    "declared_by": "u-test-001",
                    "mitigated_at": None,
                    "resolved_at": None,
                    "resolution_summary": None,
                    "postmortem": None,
                    "postmortem_generated_at": None,
                    "similar_incidents": None,
                    "created_at": "2026-03-06 12:00:00",
                    "updated_at": "2026-03-06 12:00:00",
                }]
            else:
                result.mappings.return_value.first.return_value = {"cnt": 1}
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.get("/api/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert "incidents" in data
    assert "total" in data
    assert data["total"] == 1


# --- GET /api/incidents/{id} ---

def test_get_incident_not_found(admin_client):
    """GET nonexistent incident returns 404."""
    resp = admin_client.get("/api/incidents/nonexistent")
    assert resp.status_code == 404


def test_get_incident_detail(admin_client):
    """GET existing incident returns full detail with timeline and hypotheses."""
    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Incident detail
                result.mappings.return_value.first.return_value = {
                    "id": "inc-001",
                    "org_id": "org-test-001",
                    "alert_id": None,
                    "project_id": "proj-001",
                    "project_name": "Test Project",
                    "title": "Incidente de teste",
                    "description": None,
                    "severity": "high",
                    "status": "investigating",
                    "declared_by": "u-test-001",
                    "declared_by_name": "Test User",
                    "declared_at": "2026-03-06 12:00:00",
                    "mitigated_at": None,
                    "resolved_at": None,
                    "resolution_summary": None,
                    "postmortem": None,
                    "postmortem_generated_at": None,
                    "similar_incidents": None,
                    "created_at": "2026-03-06 12:00:00",
                    "updated_at": "2026-03-06 12:00:00",
                }
            elif call_count == 2:
                # Timeline
                result.mappings.return_value.all.return_value = [{
                    "id": "tl-001",
                    "incident_id": "inc-001",
                    "event_type": "declared",
                    "content": "Incidente declarado",
                    "created_by": "u-test-001",
                    "author_name": "Test User",
                    "is_ai_generated": False,
                    "metadata": None,
                    "created_at": "2026-03-06 12:00:00",
                }]
            else:
                # Hypotheses
                result.mappings.return_value.all.return_value = [{
                    "id": "hyp-001",
                    "incident_id": "inc-001",
                    "hypothesis": "Deploy recente causou regressao",
                    "reasoning": "Mudanca no servico de pagamento 2h antes",
                    "confidence": 0.85,
                    "status": "open",
                    "confirmed_by": None,
                    "confirmed_by_name": None,
                    "created_at": "2026-03-06 12:05:00",
                }]
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.get("/api/incidents/inc-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "inc-001"
    assert len(data["timeline"]) == 1
    assert len(data["hypotheses"]) == 1
    assert data["hypotheses"][0]["confidence"] == 0.85


# --- PATCH /api/incidents/{id}/status ---

def test_update_status_valid_transition(admin_client):
    """Valid status transition works."""
    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Fetch incident
                result.mappings.return_value.first.return_value = {
                    "id": "inc-001",
                    "status": "open",
                    "org_id": "org-test-001",
                }
            else:
                result.rowcount = 1
                result.mappings.return_value.first.return_value = None
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.patch("/api/incidents/inc-001/status", json={
        "status": "investigating",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "investigating"


def test_update_status_invalid_transition(admin_client):
    """Invalid transition returns 400."""
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
                    "id": "inc-001",
                    "status": "open",
                    "org_id": "org-test-001",
                }
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.patch("/api/incidents/inc-001/status", json={
        "status": "resolved",
    })
    assert resp.status_code == 400


# --- POST /api/incidents/{id}/timeline ---

def test_add_timeline_event(admin_client):
    """Add event to incident timeline."""
    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.mappings.return_value.first.return_value = {"id": "inc-001"}
            else:
                result.rowcount = 1
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.post("/api/incidents/inc-001/timeline", json={
        "content": "Reiniciado servico de pagamento",
        "event_type": "action",
    })
    assert resp.status_code == 200
    assert resp.json()["event_type"] == "action"


def test_add_timeline_invalid_type(admin_client):
    """Invalid event type returns 400."""
    resp = admin_client.post("/api/incidents/inc-001/timeline", json={
        "content": "test",
        "event_type": "invalid",
    })
    assert resp.status_code == 400


# --- PATCH /api/incidents/{id}/hypotheses/{hyp_id} ---

def test_confirm_hypothesis(admin_client):
    """Confirm a hypothesis."""
    call_count = 0

    def mock_session():
        nonlocal call_count
        session = MagicMock()

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.rowcount = 1
            elif call_count == 2:
                result.mappings.return_value.first.return_value = {
                    "hypothesis": "Deploy causou regressao",
                }
            else:
                result.rowcount = 1
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.patch("/api/incidents/inc-001/hypotheses/hyp-001", json={
        "status": "confirmed",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


def test_discard_hypothesis(admin_client):
    """Discard a hypothesis."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.rowcount = 1
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.patch("/api/incidents/inc-001/hypotheses/hyp-002", json={
        "status": "discarded",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "discarded"


def test_hypothesis_not_found(admin_client):
    """Nonexistent hypothesis returns 404."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.rowcount = 0
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.patch("/api/incidents/inc-001/hypotheses/nonexistent", json={
        "status": "confirmed",
    })
    assert resp.status_code == 404


# --- GET /api/incidents/stats ---

def test_incident_stats(admin_client):
    """Stats endpoint returns correct data with enhanced metrics."""
    def mock_session():
        session = MagicMock()
        call_count = 0

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Main stats query
                result.mappings.return_value.first.return_value = {
                    "active": 3,
                    "resolved_month": 7,
                    "total": 15,
                    "avg_hours": 2.5,
                    "avg_hours_7d": 2.0,
                    "avg_hours_prev": 3.0,
                }
            else:
                # Most affected project query
                result.mappings.return_value.first.return_value = {
                    "name": "API Backend",
                    "cnt": 5,
                }
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.get("/api/incidents/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] == 3
    assert data["resolved_month"] == 7
    assert data["total"] == 15
    assert data["avg_resolution_hours"] == 2.5
    assert data["avg_resolution_hours_7d"] == 2.0
    assert data["mttr_trend"] == -33.3
    assert data["most_affected_project"] == "API Backend"
    assert data["most_affected_count"] == 5


# --- IncidentAnalyzer ---

@patch("app.core.incident_analyzer.llm_router")
def test_incident_analyzer_generates_hypotheses(mock_llm):
    """IncidentAnalyzer generates and saves hypotheses."""
    import json
    from app.core.incident_analyzer import IncidentAnalyzer

    mock_llm.complete.return_value = {
        "content": json.dumps([
            {"hypothesis": "Deploy recente", "reasoning": "Mudanca 2h antes", "confidence": 0.85},
            {"hypothesis": "Sobrecarga", "reasoning": "Pico de trafego", "confidence": 0.6},
        ])
    }

    db = MagicMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Incident
            result.mappings.return_value.first.return_value = {
                "id": "inc-001",
                "org_id": "org-test-001",
                "alert_id": "alert-001",
                "project_id": "proj-001",
                "title": "Erro no pagamento",
                "description": None,
            }
        elif call_count == 2:
            # Alert + log
            result.mappings.return_value.first.return_value = {
                "explanation": "Timeout no gateway",
                "stack_trace": "Traceback...",
                "log_message": "Connection refused",
            }
        elif call_count == 3:
            # Recent logs
            result.mappings.return_value.all.return_value = []
        elif call_count == 4:
            # Recent PRs
            result.mappings.return_value.all.return_value = []
        elif call_count == 5:
            # Past incidents
            result.mappings.return_value.all.return_value = []
        else:
            result.rowcount = 1
            result.mappings.return_value.first.return_value = None
        return result

    db.execute = mock_execute

    analyzer = IncidentAnalyzer(db, "org-test-001")
    analyzer.generate_hypotheses("inc-001")

    assert mock_llm.complete.called
    assert db.commit.called


# --- PostmortemGenerator ---

@patch("app.core.postmortem_generator.llm_router")
def test_postmortem_generator(mock_llm):
    """PostmortemGenerator generates markdown post-mortem."""
    from app.core.postmortem_generator import generate

    mock_llm.complete.return_value = {
        "content": "# Post-mortem — Erro no pagamento\n\n## Resumo\nO sistema ficou indisponivel..."
    }

    db = MagicMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.mappings.return_value.first.return_value = {
                "id": "inc-001",
                "org_id": "org-test-001",
                "title": "Erro no pagamento",
                "severity": "critical",
                "status": "resolved",
                "declared_at": "2026-03-06 10:00:00",
                "resolved_at": "2026-03-06 12:00:00",
                "resolution_summary": "Reiniciado gateway",
            }
        elif call_count == 2:
            result.mappings.return_value.all.return_value = [{
                "event_type": "declared",
                "content": "Incidente declarado",
                "is_ai_generated": False,
                "created_at": "2026-03-06 10:00:00",
                "created_by": "u-test-001",
            }]
        elif call_count == 3:
            result.mappings.return_value.all.return_value = [{
                "hypothesis": "Deploy recente",
                "reasoning": "Mudanca 2h antes",
                "confidence": 0.85,
                "status": "confirmed",
            }]
        else:
            result.rowcount = 1
        return result

    db.execute = mock_execute

    md = generate(db, "inc-001", "org-test-001")
    assert md is not None
    assert "Post-mortem" in md
    assert mock_llm.complete.called
    assert db.commit.called


# ==================== Phase 2 Tests ====================


# --- Watchdog ---

def test_watchdog_check_suporte_forbidden(suporte_client):
    """Suporte cannot trigger watchdog check."""
    resp = suporte_client.post("/api/incidents/watchdog/check")
    assert resp.status_code == 403


@patch("app.core.incident_watchdog.email_client")
def test_watchdog_check_admin(mock_email, admin_client):
    """Admin can trigger watchdog check."""
    mock_email.build_incident_no_update_email.return_value = ("Subj", "Body")
    mock_email.send_to_org_admins.return_value = 0

    def mock_session():
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.post("/api/incidents/watchdog/check")
    assert resp.status_code == 200
    assert "reminders_sent" in resp.json()


@patch("app.core.incident_watchdog.email_client")
def test_watchdog_sends_reminders(mock_email):
    """Watchdog detects stale incidents and sends reminders."""
    from app.core.incident_watchdog import check_stale_incidents

    mock_email.build_incident_no_update_email.return_value = ("Subject", "Body")
    mock_email.send_to_org_admins.return_value = 1

    db = MagicMock()
    db.execute.return_value.mappings.return_value.all.return_value = [
        {
            "id": "inc-stale-001",
            "org_id": "org-test-001",
            "title": "Erro critico",
            "status": "open",
            "project_id": "proj-001",
            "project_name": "API",
            "last_update": "2026-03-06 08:00:00",
        }
    ]

    sent = check_stale_incidents(db)
    assert sent == 1
    mock_email.build_incident_no_update_email.assert_called_once()
    mock_email.send_to_org_admins.assert_called_once()


# --- Similar Incidents ---

def test_get_similar_incidents_not_found(admin_client):
    """Returns 404 for non-existent incident."""
    resp = admin_client.get("/api/incidents/inc-999/similar")
    assert resp.status_code == 404


def test_get_similar_incidents_cached(admin_client):
    """Returns cached similar incidents when available."""
    def mock_session():
        session = MagicMock()
        call_count = 0

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Incident exists
                result.mappings.return_value.first.return_value = {"id": "inc-001"}
            elif call_count == 2:
                # Cached similar incidents - use real dicts for dict() cast
                from types import MappingProxyType
                row = {
                    "similar_incident_id": "inc-old-001",
                    "similarity_score": 0.87,
                    "title": "Erro similar passado",
                    "severity": "high",
                    "resolved_at": "2026-02-20 14:00:00",
                    "resolution_summary": "Reiniciado o servico",
                    "project_name": "API Backend",
                }
                result.mappings.return_value.all.return_value = [row]
            return result

        session.execute = mock_execute
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.get("/api/incidents/inc-001/similar")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["similar"]) == 1
    assert data["similar"][0]["title"] == "Erro similar passado"
    assert data["similar"][0]["similarity_score"] == 0.87


@patch("app.core.incident_analyzer.Embedder")
def test_find_similar_uses_embedder(mock_embedder_cls):
    """IncidentAnalyzer.find_similar uses Embedder correctly."""
    from app.core.incident_analyzer import IncidentAnalyzer

    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536
    mock_embedder_cls.return_value = mock_embedder

    db = MagicMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # Get incident
            result.mappings.return_value.first.return_value = {
                "title": "Erro no pagamento",
                "description": "Gateway timeout",
            }
        elif call_count == 2:
            # Similar search
            result.mappings.return_value.all.return_value = [
                {
                    "id": "inc-old-001",
                    "title": "Timeout anterior",
                    "severity": "high",
                    "resolved_at": "2026-02-15",
                    "resolution_summary": "Fix no gateway",
                    "project_name": "API",
                    "similarity": 0.82,
                }
            ]
        else:
            result.rowcount = 1
        return result

    db.execute = mock_execute

    analyzer = IncidentAnalyzer(db, "org-test-001")
    results = analyzer.find_similar("inc-001")

    mock_embedder.embed_text.assert_called_once()
    assert len(results) == 1
    assert results[0]["title"] == "Timeout anterior"
    assert results[0]["similarity"] == 0.82


# --- Share Token ---

def test_create_share_token(admin_client):
    """Creates share token for incident with post-mortem."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.mappings.return_value.first.return_value = {
            "id": "inc-001",
            "share_token": None,
            "postmortem": "# Post-mortem\n\nConteudo aqui",
        }
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.post("/api/incidents/inc-001/share")
    assert resp.status_code == 200
    data = resp.json()
    assert "share_token" in data
    assert "public_url" in data
    assert len(data["share_token"]) > 10


def test_create_share_token_no_postmortem(admin_client):
    """Cannot share if no post-mortem exists."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.mappings.return_value.first.return_value = {
            "id": "inc-001",
            "share_token": None,
            "postmortem": None,
        }
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.post("/api/incidents/inc-001/share")
    assert resp.status_code == 400


def test_create_share_token_returns_existing(admin_client):
    """Returns existing token if already shared."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.mappings.return_value.first.return_value = {
            "id": "inc-001",
            "share_token": "existing-token-abc",
            "postmortem": "# Post-mortem",
        }
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.post("/api/incidents/inc-001/share")
    assert resp.status_code == 200
    assert resp.json()["share_token"] == "existing-token-abc"


def test_revoke_share_token(admin_client):
    """Revokes share token."""
    resp = admin_client.delete("/api/incidents/inc-001/share")
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"


def test_revoke_share_token_not_found(admin_client):
    """Returns 404 when revoking non-existent incident."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.rowcount = 0
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    resp = admin_client.delete("/api/incidents/inc-999/share")
    assert resp.status_code == 404


# --- Public Postmortem ---

def test_public_postmortem():
    """Public postmortem endpoint returns data without auth."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.mappings.return_value.first.return_value = {
            "title": "Erro critico no pagamento",
            "severity": "critical",
            "declared_at": "2026-03-06 10:00:00",
            "resolved_at": "2026-03-06 12:00:00",
            "postmortem": "# Post-mortem\n\n## Resumo\nO sistema ficou fora.",
            "postmortem_generated_at": "2026-03-06 13:00:00",
            "project_name": "API Backend",
        }
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    client = TestClient(app)
    resp = client.get("/api/postmortem/valid-token-abc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Erro critico no pagamento"
    assert data["severity"] == "critical"
    assert "Post-mortem" in data["postmortem"]
    assert data["project_name"] == "API Backend"
    assert data["postmortem_generated_at"] is not None
    app.dependency_overrides.clear()


def test_public_postmortem_invalid_token():
    """Returns 404 for invalid share token."""
    def mock_session():
        session = MagicMock()
        result = MagicMock()
        result.mappings.return_value.first.return_value = None
        session.execute.return_value = result
        return session

    app.dependency_overrides[get_session] = mock_session
    app.dependency_overrides[get_data_session] = mock_session
    client = TestClient(app)
    resp = client.get("/api/postmortem/invalid-token-xyz")
    assert resp.status_code == 404
    app.dependency_overrides.clear()


# --- Share token role restrictions ---

def test_share_token_suporte_forbidden(suporte_client):
    """Suporte cannot create share tokens."""
    resp = suporte_client.post("/api/incidents/inc-001/share")
    assert resp.status_code == 403


def test_similar_incidents_suporte_forbidden(suporte_client):
    """Suporte cannot access similar incidents."""
    resp = suporte_client.get("/api/incidents/inc-001/similar")
    assert resp.status_code == 403
