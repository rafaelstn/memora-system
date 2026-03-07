"""Tests for Module 10 — Executive Dashboard."""
import json
from unittest.mock import MagicMock, patch

import pytest


# ────────────────────── API Endpoints ──────────────────────

def test_latest_snapshot_not_found(admin_client):
    from app.api.deps import get_session
    from app.main import app

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_db
    resp = admin_client.get("/api/executive/snapshot/latest")
    assert resp.status_code == 404


def test_latest_snapshot_ok(admin_client):
    from app.api.deps import get_session
    from app.main import app

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "id": "snap-1",
        "org_id": "org-test-001",
        "generated_at": "2026-03-06T10:00:00",
        "period_start": "2026-02-27T10:00:00",
        "period_end": "2026-03-06T10:00:00",
        "health_score": 85,
        "summary": "Semana estavel",
        "highlights": "[]",
        "risks": "[]",
        "recommendations": "[]",
        "metrics": "{}",
    }
    app.dependency_overrides[get_session] = lambda: mock_db
    resp = admin_client.get("/api/executive/snapshot/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["health_score"] == 85
    assert data["id"] == "snap-1"


def test_snapshot_history(admin_client):
    from app.api.deps import get_session
    from app.main import app

    mock_db = MagicMock()
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.mappings.return_value.all.return_value = [
                {
                    "id": "snap-1",
                    "generated_at": "2026-03-06T10:00:00",
                    "period_start": "2026-02-27T10:00:00",
                    "period_end": "2026-03-06T10:00:00",
                    "health_score": 85,
                    "summary": "OK",
                },
            ]
        else:
            result.mappings.return_value.first.return_value = {"cnt": 1}
        return result

    mock_db.execute.side_effect = side_effect
    app.dependency_overrides[get_session] = lambda: mock_db
    resp = admin_client.get("/api/executive/snapshot/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["snapshots"]) == 1


def test_realtime_metrics(admin_client):
    from app.api.deps import get_session
    from app.main import app

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {"cnt": 3}
    app.dependency_overrides[get_session] = lambda: mock_db
    resp = admin_client.get("/api/executive/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "systems_monitored" in data
    assert "alerts_open" in data
    assert "incidents_open" in data
    assert "repos_indexed" in data


def test_generate_snapshot(admin_client):
    from app.api.deps import get_session
    from app.main import app

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "total": 0, "critical": 0, "high": 0, "open_alerts": 0, "resolved": 0,
        "cnt": 0,
    }
    mock_db.execute.return_value.mappings.return_value.all.return_value = []
    app.dependency_overrides[get_session] = lambda: mock_db

    with patch("app.core.executive_reporter.llm_router") as mock_llm:
        mock_llm.complete.return_value = {
            "content": json.dumps({
                "health_score": 92,
                "summary": "Tudo otimo",
                "highlights": [{"type": "positive", "text": "Sistema estavel"}],
                "risks": [],
                "recommendations": [{"priority": 1, "action": "Continuar", "reason": "OK"}],
            }),
        }
        resp = admin_client.get("/api/executive/snapshot/generate?period=week")
        assert resp.status_code == 200
        data = resp.json()
        assert data["health_score"] == 92
        assert len(data["highlights"]) == 1


def test_generate_snapshot_fallback(admin_client):
    from app.api.deps import get_session
    from app.main import app

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "total": 0, "critical": 0, "high": 0, "open_alerts": 0, "resolved": 0,
        "cnt": 0,
    }
    mock_db.execute.return_value.mappings.return_value.all.return_value = []
    app.dependency_overrides[get_session] = lambda: mock_db

    with patch("app.core.executive_reporter.llm_router") as mock_llm:
        mock_llm.complete.side_effect = Exception("LLM down")
        resp = admin_client.get("/api/executive/snapshot/generate")
        assert resp.status_code == 200
        data = resp.json()
        assert "health_score" in data
        assert isinstance(data["health_score"], int)


def test_executive_admin_only(dev_client, suporte_client):
    for client in [dev_client, suporte_client]:
        resp = client.get("/api/executive/snapshot/latest")
        assert resp.status_code == 403

        resp = client.get("/api/executive/metrics")
        assert resp.status_code == 403


# ────────────────────── Core Logic ──────────────────────

def test_executive_reporter_collect_metrics():
    from app.core.executive_reporter import ExecutiveReporter
    from datetime import datetime, timedelta

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "total": 5, "critical": 1, "high": 2, "open_alerts": 3, "resolved": 2,
        "cnt": 4,
    }
    mock_db.execute.return_value.mappings.return_value.all.return_value = []

    reporter = ExecutiveReporter(mock_db, "org-test-001")
    now = datetime.utcnow()
    metrics = reporter._collect_metrics(now - timedelta(days=7), now)
    assert "alertas" in metrics
    assert "incidentes" in metrics
    assert "repositorios" in metrics


def test_executive_reporter_fallback():
    from app.core.executive_reporter import ExecutiveReporter

    mock_db = MagicMock()
    reporter = ExecutiveReporter(mock_db, "org-test-001")
    result = reporter._fallback_snapshot({
        "alertas": {"critical": 2, "high": 3},
        "incidentes": {"ativos": 1},
    })
    assert result["health_score"] < 100
    assert result["health_score"] >= 0


def test_realtime_metrics_function():
    from app.core.executive_reporter import get_realtime_metrics

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {"cnt": 2}

    result = get_realtime_metrics(mock_db, "org-test-001")
    assert result["systems_monitored"] == 2
    assert result["alerts_open"] == 2
    assert result["incidents_open"] == 2
    assert result["repos_indexed"] == 2


def test_realtime_metrics_exception():
    from app.core.executive_reporter import get_realtime_metrics

    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB down")

    result = get_realtime_metrics(mock_db, "org-test-001")
    assert result["systems_monitored"] == 0
    assert result["alerts_open"] == 0
