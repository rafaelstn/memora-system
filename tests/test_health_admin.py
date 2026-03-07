"""Tests for the admin health check endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_session
from app.main import app
from tests.conftest import _fake_user


def _mock_session():
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    # Mock execute for SQL queries
    session.execute.return_value.mappings.return_value.all.return_value = []
    session.execute.return_value.mappings.return_value.first.return_value = {
        "chunks_total": 1000,
        "repos_indexed": 3,
        "last_indexed_at": "2026-03-07 10:00:00",
        "last_event": None,
    }
    return session


class TestHealthAdminEndpoint:
    def test_admin_gets_health_status(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = _mock_session
        client = TestClient(app)

        with patch("app.api.routes.health_admin._check_database") as mock_db, \
             patch("app.api.routes.health_admin._check_embeddings") as mock_emb:
            mock_db.return_value = {"status": "ok", "latency_ms": 23, "detail": "PostgreSQL — Supabase"}
            mock_emb.return_value = {"status": "ok", "provider": "openai", "latency_ms": 150, "detail": "OpenAI text-embedding-3-small"}

            res = client.get("/api/health/admin")
            assert res.status_code == 200
            data = res.json()

            assert "database" in data
            assert "embeddings" in data
            assert "llm_providers" in data
            assert "github_webhook" in data
            assert "background_workers" in data
            assert "email" in data
            assert "storage" in data

        app.dependency_overrides.clear()

    def test_database_latency_measured(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = _mock_session
        client = TestClient(app)

        with patch("app.api.routes.health_admin._check_database") as mock_db, \
             patch("app.api.routes.health_admin._check_embeddings") as mock_emb:
            mock_db.return_value = {"status": "ok", "latency_ms": 42, "detail": "PostgreSQL — Supabase"}
            mock_emb.return_value = {"status": "ok", "provider": "openai", "latency_ms": 100, "detail": "OK"}

            res = client.get("/api/health/admin")
            data = res.json()
            assert data["database"]["latency_ms"] == 42

        app.dependency_overrides.clear()

    def test_unconfigured_component_returns_not_configured(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = _mock_session
        client = TestClient(app)

        with patch("app.api.routes.health_admin._check_database") as mock_db, \
             patch("app.api.routes.health_admin._check_embeddings") as mock_emb, \
             patch("app.api.routes.health_admin.settings") as mock_settings:
            mock_db.return_value = {"status": "ok", "latency_ms": 10, "detail": "OK"}
            mock_emb.return_value = {"status": "ok", "provider": "openai", "latency_ms": 100, "detail": "OK"}
            mock_settings.smtp_host = ""
            mock_settings.github_webhook_secret = ""

            res = client.get("/api/health/admin")
            data = res.json()
            assert data["email"]["status"] == "not_configured"
            assert data["github_webhook"]["status"] == "not_configured"

        app.dependency_overrides.clear()

    def test_dev_cannot_access_health_admin(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("dev")
        app.dependency_overrides[get_session] = _mock_session
        client = TestClient(app)

        res = client.get("/api/health/admin")
        assert res.status_code == 403

        app.dependency_overrides.clear()

    def test_suporte_cannot_access_health_admin(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("suporte")
        app.dependency_overrides[get_session] = _mock_session
        client = TestClient(app)

        res = client.get("/api/health/admin")
        assert res.status_code == 403

        app.dependency_overrides.clear()

    def test_all_components_returned(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = _mock_session
        client = TestClient(app)

        with patch("app.api.routes.health_admin._check_database") as mock_db, \
             patch("app.api.routes.health_admin._check_embeddings") as mock_emb:
            mock_db.return_value = {"status": "ok", "latency_ms": 5, "detail": "OK"}
            mock_emb.return_value = {"status": "ok", "provider": "openai", "latency_ms": 50, "detail": "OK"}

            res = client.get("/api/health/admin")
            data = res.json()
            expected_keys = {"database", "embeddings", "llm_providers", "github_webhook", "background_workers", "email", "storage"}
            assert set(data.keys()) == expected_keys

        app.dependency_overrides.clear()

    def test_background_workers_always_ok(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = _mock_session
        client = TestClient(app)

        with patch("app.api.routes.health_admin._check_database") as mock_db, \
             patch("app.api.routes.health_admin._check_embeddings") as mock_emb:
            mock_db.return_value = {"status": "ok", "latency_ms": 5, "detail": "OK"}
            mock_emb.return_value = {"status": "ok", "provider": "openai", "latency_ms": 50, "detail": "OK"}

            res = client.get("/api/health/admin")
            data = res.json()
            assert data["background_workers"]["status"] == "ok"
            assert data["background_workers"]["active_jobs"] == 0
            assert data["background_workers"]["failed_jobs_last_hour"] == 0

        app.dependency_overrides.clear()
