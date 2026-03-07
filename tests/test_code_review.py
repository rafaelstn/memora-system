"""Testes do Modulo 4 — Revisao de Codigo (reviews, findings, webhook PR, manual review)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_session


# --- Helpers ---


def _mock_review_db():
    """Mock DB with review-specific defaults."""
    db = MagicMock()
    db.execute.return_value.mappings.return_value.all.return_value = []
    db.execute.return_value.mappings.return_value.first.return_value = None
    db.execute.return_value.first.return_value = None
    db.execute.return_value.scalar.return_value = 0
    db.execute.return_value.rowcount = 1
    return db


# --- POST /api/reviews/manual ---


def test_create_manual_review(admin_client):
    """POST /api/reviews/manual creates a review and returns review_id."""
    resp = admin_client.post("/api/reviews/manual", json={
        "code": "def foo():\n    return 1 / 0",
        "language": "python",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "review_id" in data
    assert data["status"] == "analyzing"


def test_create_manual_review_empty_code(admin_client):
    """POST /api/reviews/manual with empty code fails."""
    resp = admin_client.post("/api/reviews/manual", json={
        "code": "",
        "language": "python",
    })
    assert resp.status_code == 400


def test_create_manual_review_suporte_forbidden(suporte_client):
    """POST /api/reviews/manual forbidden for suporte role."""
    resp = suporte_client.post("/api/reviews/manual", json={
        "code": "print('hello')",
        "language": "python",
    })
    assert resp.status_code == 403


def test_create_manual_review_dev_allowed(dev_client):
    """POST /api/reviews/manual allowed for dev role."""
    resp = dev_client.post("/api/reviews/manual", json={
        "code": "print('hello')",
        "language": "python",
    })
    assert resp.status_code == 200
    assert "review_id" in resp.json()


# --- GET /api/reviews ---


def test_list_reviews(admin_client):
    """GET /api/reviews returns list."""
    resp = admin_client.get("/api/reviews")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_reviews_with_filters(admin_client):
    """GET /api/reviews with source_type and verdict filters."""
    resp = admin_client.get("/api/reviews?source_type=pr&verdict=approved")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_reviews_suporte_forbidden(suporte_client):
    """GET /api/reviews forbidden for suporte role."""
    resp = suporte_client.get("/api/reviews")
    assert resp.status_code == 403


# --- GET /api/reviews/stats ---


def test_review_stats(admin_client):
    """GET /api/reviews/stats returns statistics."""
    db = _mock_review_db()
    # Mock the complex stats query — returns dict-like mapping
    stats_row = MagicMock()
    stats_row.__getitem__ = lambda self, key: {
        "total": 5, "avg_score": 78.5, "approved_count": 3, "this_month": 2,
    }.get(key, 0)
    stats_row.get = lambda key, default=None: {
        "total": 5, "avg_score": 78.5, "approved_count": 3, "this_month": 2,
    }.get(key, default)

    critical_row = MagicMock()
    critical_row.__getitem__ = lambda self, key: {"cnt": 1}.get(key, 0)

    # Chain returns: first call = stats, second = critical, third = weekly, fourth = by_category
    call_count = {"n": 0}
    original_execute = db.execute

    def mock_execute(*args, **kwargs):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.mappings.return_value.first.return_value = stats_row
        elif call_count["n"] == 2:
            result.mappings.return_value.first.return_value = critical_row
        elif call_count["n"] == 3:
            result.mappings.return_value.all.return_value = []
        elif call_count["n"] == 4:
            result.mappings.return_value.all.return_value = []
        return result

    db.execute = mock_execute
    app.dependency_overrides[get_session] = lambda: db
    try:
        resp = admin_client.get("/api/reviews/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_reviews" in data
        assert data["total_reviews"] == 5
        assert "weekly_trend" in data
        assert "findings_by_category" in data
    finally:
        from tests.conftest import _mock_session
        app.dependency_overrides[get_session] = _mock_session


# --- GET /api/reviews/{id} ---


def test_get_review_not_found(admin_client):
    """GET /api/reviews/{id} returns 404 for unknown review."""
    db = _mock_review_db()
    db.execute.return_value.mappings.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: db
    try:
        resp = admin_client.get("/api/reviews/nonexistent-id")
        assert resp.status_code == 404
    finally:
        from tests.conftest import _mock_session
        app.dependency_overrides[get_session] = _mock_session


# --- DELETE /api/reviews/{id} ---


def test_delete_review(admin_client):
    """DELETE /api/reviews/{id} removes the review."""
    resp = admin_client.delete("/api/reviews/review-test-001")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_delete_review_not_found(admin_client):
    """DELETE /api/reviews/{id} returns 404 if not found."""
    db = _mock_review_db()
    db.execute.return_value.rowcount = 0
    app.dependency_overrides[get_session] = lambda: db
    try:
        resp = admin_client.delete("/api/reviews/nonexistent-id")
        assert resp.status_code == 404
    finally:
        from tests.conftest import _mock_session
        app.dependency_overrides[get_session] = _mock_session


# --- Unit tests: code_reviewer ---


def test_parse_findings_json_valid():
    """Parse valid JSON array of findings."""
    from app.core.code_reviewer import _parse_findings_json

    response = json.dumps([
        {
            "title": "SQL Injection",
            "description": "Input nao sanitizado",
            "suggestion": "Usar parametros bind",
            "severity": "critical",
            "file_path": "app/routes.py",
            "line_start": 42,
            "line_end": 45,
            "code_snippet": "db.execute(f'SELECT * FROM {table}')",
        }
    ])
    result = _parse_findings_json(response)
    assert len(result) == 1
    assert result[0]["title"] == "SQL Injection"
    assert result[0]["severity"] == "critical"


def test_parse_findings_json_empty():
    """Parse empty array response."""
    from app.core.code_reviewer import _parse_findings_json

    result = _parse_findings_json("[]")
    assert result == []


def test_parse_findings_json_markdown_fences():
    """Parse JSON wrapped in markdown code fences."""
    from app.core.code_reviewer import _parse_findings_json

    response = '```json\n[{"title": "Bug", "description": "desc", "severity": "medium"}]\n```'
    result = _parse_findings_json(response)
    assert len(result) == 1
    assert result[0]["title"] == "Bug"


def test_parse_findings_json_invalid():
    """Parse invalid JSON returns empty list."""
    from app.core.code_reviewer import _parse_findings_json

    result = _parse_findings_json("This is not JSON at all")
    assert result == []


def test_parse_findings_json_with_text():
    """Parse JSON array embedded in surrounding text."""
    from app.core.code_reviewer import _parse_findings_json

    response = 'Here are the findings:\n[{"title": "Issue", "description": "desc", "severity": "low"}]\nEnd.'
    result = _parse_findings_json(response)
    assert len(result) == 1


def test_calculate_score():
    """Score calculation deducts correctly by severity."""
    from app.core.code_reviewer import CodeReviewer

    reviewer = CodeReviewer.__new__(CodeReviewer)
    findings = [
        {"severity": "critical"},
        {"severity": "high"},
        {"severity": "medium"},
        {"severity": "low"},
        {"severity": "info"},
    ]
    score = reviewer._calculate_score(findings)
    # 100 - 25 - 15 - 8 - 3 - 1 = 48
    assert score == 48


def test_calculate_score_empty():
    """Empty findings = score 100."""
    from app.core.code_reviewer import CodeReviewer

    reviewer = CodeReviewer.__new__(CodeReviewer)
    assert reviewer._calculate_score([]) == 100


def test_calculate_score_min_zero():
    """Score never goes below 0."""
    from app.core.code_reviewer import CodeReviewer

    reviewer = CodeReviewer.__new__(CodeReviewer)
    findings = [{"severity": "critical"}] * 10  # -250 -> clamped to 0
    assert reviewer._calculate_score(findings) == 0


def test_calculate_verdict_approved():
    """High score, no critical/high -> approved."""
    from app.core.code_reviewer import CodeReviewer

    reviewer = CodeReviewer.__new__(CodeReviewer)
    assert reviewer._calculate_verdict(90, []) == "approved"
    assert reviewer._calculate_verdict(90, [{"severity": "low"}]) == "approved"


def test_calculate_verdict_with_warnings():
    """Score 70-84 without critical -> approved_with_warnings."""
    from app.core.code_reviewer import CodeReviewer

    reviewer = CodeReviewer.__new__(CodeReviewer)
    assert reviewer._calculate_verdict(75, [{"severity": "medium"}]) == "approved_with_warnings"


def test_calculate_verdict_needs_changes():
    """Score 50-69 or has high -> needs_changes."""
    from app.core.code_reviewer import CodeReviewer

    reviewer = CodeReviewer.__new__(CodeReviewer)
    assert reviewer._calculate_verdict(60, [{"severity": "medium"}]) == "needs_changes"
    assert reviewer._calculate_verdict(75, [{"severity": "high"}]) == "needs_changes"


def test_calculate_verdict_rejected():
    """Score < 50 or has critical -> rejected."""
    from app.core.code_reviewer import CodeReviewer

    reviewer = CodeReviewer.__new__(CodeReviewer)
    assert reviewer._calculate_verdict(30, []) == "rejected"
    assert reviewer._calculate_verdict(90, [{"severity": "critical"}]) == "rejected"


# --- Unit tests: github_commenter ---


def test_build_comment():
    """Build comment generates proper markdown."""
    from app.core.github_commenter import _build_comment

    review = {
        "overall_verdict": "approved_with_warnings",
        "overall_score": 72,
        "summary": "Codigo com algumas melhorias necessarias.",
    }
    findings = [
        {
            "category": "bug",
            "severity": "medium",
            "title": "Division by zero",
            "description": "Divisao por zero na linha 42",
            "suggestion": "Adicionar verificacao",
            "file_path": "app/calc.py",
            "line_start": 42,
            "line_end": None,
        },
        {
            "category": "security",
            "severity": "high",
            "title": "SQL Injection",
            "description": "Input concatenado na query",
            "suggestion": "Usar parametros bind",
            "file_path": "app/db.py",
            "line_start": 10,
            "line_end": 15,
        },
    ]

    comment = _build_comment(review, findings, "http://localhost:3000")
    assert "Revisao Memora" in comment
    assert "72/100" in comment
    assert "Aprovado com ressalvas" in comment
    assert "Division by zero" in comment
    assert "SQL Injection" in comment
    assert "app/calc.py:42" in comment
    assert "Memora" in comment


def test_build_comment_no_findings():
    """Build comment with no findings."""
    from app.core.github_commenter import _build_comment

    review = {
        "overall_verdict": "approved",
        "overall_score": 95,
        "summary": "Codigo excelente.",
    }

    comment = _build_comment(review, [], "http://localhost:3000")
    assert "95/100" in comment
    assert "Aprovado" in comment


# --- Webhook PR event ---


def test_webhook_pr_opened():
    """Webhook with pull_request opened event creates review."""
    from tests.conftest import _mock_session

    client = TestClient(app)
    # No signature validation needed if secret not configured
    resp = client.post(
        "/api/webhooks/github",
        json={
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "html_url": "https://github.com/owner/repo/pull/42",
                "user": {"login": "developer"},
            },
            "repository": {
                "full_name": "owner/repo",
            },
        },
        headers={
            "X-GitHub-Event": "pull_request",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["event"] == "pull_request"
    assert data["pr_number"] == 42
    assert data["status"] == "processing"


def test_webhook_pr_closed_ignored():
    """Webhook with pull_request closed event is ignored."""
    client = TestClient(app)
    resp = client.post(
        "/api/webhooks/github",
        json={
            "action": "closed",
            "pull_request": {"number": 42},
            "repository": {"full_name": "owner/repo"},
        },
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_pr_synchronize():
    """Webhook with pull_request synchronize event triggers review."""
    client = TestClient(app)
    resp = client.post(
        "/api/webhooks/github",
        json={
            "action": "synchronize",
            "pull_request": {
                "number": 7,
                "title": "Update deps",
                "html_url": "https://github.com/owner/repo/pull/7",
                "user": {"login": "dev2"},
            },
            "repository": {"full_name": "owner/repo"},
        },
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"
