"""Testes do historico executivo semanal."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ── generate_weekly_snapshot ──────────────────────────────


def test_snapshot_generates_all_metrics():
    """Snapshot gerado com os valores das metricas."""
    from app.core.executive_weekly import generate_weekly_snapshot

    mock_db = MagicMock()

    # All queries return mock values
    call_count = {"n": 0}

    def execute_side(*args, **kwargs):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # security score
            result.mappings.return_value.first.return_value = {"avg_score": 85.5}
        elif call_count["n"] == 2:
            # error alerts
            result.scalar.return_value = 12
        elif call_count["n"] == 3:
            # support questions
            result.scalar.return_value = 42
        elif call_count["n"] == 4:
            # code reviews
            result.mappings.return_value.first.return_value = {"avg_score": 78.0, "cnt": 5}
        elif call_count["n"] == 5:
            # incident resolution
            result.scalar.return_value = 3.5
        elif call_count["n"] == 6:
            # total repos
            result.scalar.return_value = 10
        elif call_count["n"] == 7:
            # documented repos
            result.scalar.return_value = 7
        else:
            result.scalar.return_value = 0
        return result

    mock_db.execute.side_effect = execute_side

    now = datetime.utcnow()
    snap = generate_weekly_snapshot(
        mock_db, "org-001", "prod-001",
        now - timedelta(days=7), now,
    )

    assert snap["security_score_avg"] == 85.5
    assert snap["error_alert_count"] == 12
    assert snap["support_question_count"] == 42
    assert snap["code_review_score_avg"] == 78.0
    assert snap["prs_reviewed_count"] == 5
    assert snap["incident_resolution_avg_hours"] == 3.5
    assert snap["doc_coverage_pct"] == 70.0


def test_snapshot_handles_empty_data():
    """Snapshot com dados vazios nao quebra."""
    from app.core.executive_weekly import generate_weekly_snapshot

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {"avg_score": None, "cnt": 0}
    mock_db.execute.return_value.scalar.return_value = 0

    now = datetime.utcnow()
    snap = generate_weekly_snapshot(
        mock_db, "org-001", "prod-001",
        now - timedelta(days=7), now,
    )

    assert snap["error_alert_count"] == 0
    assert snap["support_question_count"] == 0


def test_snapshot_handles_db_error():
    """Erro em uma metrica nao derruba o snapshot inteiro."""
    from app.core.executive_weekly import generate_weekly_snapshot

    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB error")

    now = datetime.utcnow()
    snap = generate_weekly_snapshot(
        mock_db, "org-001", "prod-001",
        now - timedelta(days=7), now,
    )

    # Should return defaults, not raise
    assert snap["error_alert_count"] == 0
    assert snap["security_score_avg"] is None


# ── get_history ──────────────────────────────


def test_get_history_period_filter():
    """Filtro de periodo retorna quantidade correta."""
    from app.core.executive_weekly import get_history

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = [
        {"id": "1", "week_start": "2026-03-01"},
        {"id": "2", "week_start": "2026-03-08"},
    ]

    result = get_history(mock_db, "org-001", "prod-001", "4w")
    assert len(result) == 2

    # Check period mapping
    from app.core.executive_weekly import get_history
    get_history(mock_db, "org-001", "prod-001", "3m")
    get_history(mock_db, "org-001", "prod-001", "6m")


# ── get_history_csv ──────────────────────────────


def test_csv_export_has_headers():
    """CSV exportado tem todas as colunas."""
    from app.core.executive_weekly import get_history_csv

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = [
        {
            "id": "1",
            "week_start": "2026-03-01",
            "week_end": "2026-03-08",
            "security_score_avg": 85.0,
            "error_alert_count": 5,
            "support_question_count": 20,
            "code_review_score_avg": 78.0,
            "prs_reviewed_count": 3,
            "incident_resolution_avg_hours": 2.5,
            "doc_coverage_pct": 70.0,
        },
    ]

    csv = get_history_csv(mock_db, "org-001", "prod-001", "4w")
    lines = csv.strip().split("\n")
    assert len(lines) == 2  # header + 1 data row
    assert "week_start" in lines[0]
    assert "security_score_avg" in lines[0]
    assert "85.0" in lines[1]


# ── Routes ──────────────────────────────


@patch("app.core.executive_weekly.get_history")
def test_history_route_admin(mock_get, admin_client):
    """Admin pode acessar historico."""
    mock_get.return_value = []
    response = admin_client.get("/api/executive/history?period=4w")
    assert response.status_code == 200


def test_history_route_blocked_for_dev(dev_client):
    """Dev nao acessa historico executivo."""
    response = dev_client.get("/api/executive/history?period=4w")
    assert response.status_code == 403


def test_history_route_blocked_for_suporte(suporte_client):
    """Suporte nao acessa historico executivo."""
    response = suporte_client.get("/api/executive/history?period=4w")
    assert response.status_code == 403


@patch("app.core.executive_weekly.get_history_csv")
def test_csv_route_returns_csv(mock_csv, admin_client):
    """CSV route retorna content-type correto."""
    mock_csv.return_value = "week_start,error_count\n2026-03-01,5"
    response = admin_client.get("/api/executive/history/csv?period=4w")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")


def test_history_invalid_period(admin_client):
    """Periodo invalido retorna 422."""
    response = admin_client.get("/api/executive/history?period=invalid")
    assert response.status_code == 422


# ── Scheduler ──────────────────────────────


def test_scheduler_snapshot_check():
    """_should_run_snapshot retorna True na segunda 03h UTC."""
    from app.core.scheduler import _should_run_snapshot

    monday_3h = datetime(2026, 3, 9, 3, 2)  # Monday
    assert _should_run_snapshot(monday_3h) is True

    tuesday_3h = datetime(2026, 3, 10, 3, 2)  # Tuesday
    assert _should_run_snapshot(tuesday_3h) is False
