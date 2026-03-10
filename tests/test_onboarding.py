"""Tests for the onboarding setup flow."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_session
from app.main import app
from app.models.organization import Organization
from tests.conftest import _fake_user


def _fake_org(onboarding_completed=False, onboarding_step=0, name="Test Org"):
    org = MagicMock(spec=Organization)
    org.id = "org-test-001"
    org.name = name
    org.slug = "test-org"
    org.onboarding_completed = onboarding_completed
    org.onboarding_step = onboarding_step
    org.onboarding_completed_at = None
    org.settings = {}
    org.mode = "saas"
    return org


def _mock_session_with_org(org=None):
    session = MagicMock()
    if org is None:
        org = _fake_org()
    session.query.return_value.filter.return_value.first.return_value = org
    return session


# --- GET /api/organizations/onboarding ---


class TestGetOnboardingStatus:
    def test_admin_gets_onboarding_status(self):
        org = _fake_org(onboarding_completed=False, onboarding_step=2)
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.get("/api/organizations/onboarding")
        assert res.status_code == 200
        data = res.json()
        assert data["onboarding_completed"] is False
        assert data["onboarding_step"] == 2
        assert data["onboarding_completed_at"] is None

        app.dependency_overrides.clear()

    def test_dev_gets_onboarding_status(self):
        org = _fake_org(onboarding_completed=True, onboarding_step=5)
        app.dependency_overrides[get_current_user] = lambda: _fake_user("dev")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.get("/api/organizations/onboarding")
        assert res.status_code == 200
        data = res.json()
        assert data["onboarding_completed"] is True
        assert data["onboarding_step"] == 5

        app.dependency_overrides.clear()

    def test_suporte_gets_onboarding_status(self):
        org = _fake_org()
        app.dependency_overrides[get_current_user] = lambda: _fake_user("suporte")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.get("/api/organizations/onboarding")
        assert res.status_code == 200

        app.dependency_overrides.clear()

    def test_org_not_found_returns_404(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)

        res = client.get("/api/organizations/onboarding")
        assert res.status_code == 404

        app.dependency_overrides.clear()


# --- PATCH /api/organizations/onboarding ---


class TestUpdateOnboarding:
    def test_admin_updates_step(self):
        org = _fake_org(onboarding_step=1)
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.patch("/api/organizations/onboarding", json={"step": 3})
        assert res.status_code == 200
        data = res.json()
        assert data["onboarding_step"] == 3
        assert data["onboarding_completed"] is False

        app.dependency_overrides.clear()

    def test_admin_completes_onboarding(self):
        org = _fake_org(onboarding_step=4)
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.patch("/api/organizations/onboarding", json={"step": 5, "completed": True})
        assert res.status_code == 200
        data = res.json()
        assert data["onboarding_completed"] is True
        assert data["onboarding_completed_at"] is not None

        app.dependency_overrides.clear()

    def test_dev_cannot_update_onboarding(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("dev")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org()
        client = TestClient(app)

        res = client.patch("/api/organizations/onboarding", json={"step": 2})
        assert res.status_code == 403

        app.dependency_overrides.clear()

    def test_suporte_cannot_update_onboarding(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("suporte")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org()
        client = TestClient(app)

        res = client.patch("/api/organizations/onboarding", json={"step": 2})
        assert res.status_code == 403

        app.dependency_overrides.clear()

    def test_org_not_found_returns_404(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)

        res = client.patch("/api/organizations/onboarding", json={"step": 1})
        assert res.status_code == 404

        app.dependency_overrides.clear()


# --- PATCH /api/organizations/name ---


class TestUpdateOrgName:
    def test_admin_updates_org_name(self):
        org = _fake_org(name="Old Name")
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.patch("/api/organizations/name", json={"name": "New Name"})
        assert res.status_code == 200
        assert org.name == "New Name"

        app.dependency_overrides.clear()

    def test_admin_updates_org_name_with_app_url(self):
        org = _fake_org()
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.patch("/api/organizations/name", json={"name": "Acme", "app_url": "https://app.acme.com"})
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Acme"
        assert data["app_url"] == "https://app.acme.com"

        app.dependency_overrides.clear()

    def test_dev_cannot_update_org_name(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("dev")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org()
        client = TestClient(app)

        res = client.patch("/api/organizations/name", json={"name": "Test"})
        assert res.status_code == 403

        app.dependency_overrides.clear()


# --- /me endpoint includes onboarding fields ---


class TestMeEndpointOnboarding:
    def test_me_includes_onboarding_fields(self):
        org = _fake_org(onboarding_completed=False, onboarding_step=2)
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.get("/api/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert "onboarding_completed" in data
        assert data["onboarding_completed"] is False
        assert data["onboarding_step"] == 2

        app.dependency_overrides.clear()

    def test_me_completed_onboarding(self):
        org = _fake_org(onboarding_completed=True, onboarding_step=5)
        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: _mock_session_with_org(org)
        client = TestClient(app)

        res = client.get("/api/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert data["onboarding_completed"] is True
        assert data["onboarding_step"] == 5

        app.dependency_overrides.clear()
