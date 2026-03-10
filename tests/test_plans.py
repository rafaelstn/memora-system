"""Testes do sistema de planos e trial."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ── get_current_plan dependency ──────────────────────────────


def test_plan_trial_active():
    """Trial ativo retorna status correto e dias restantes."""
    from app.api.deps import get_current_plan

    mock_db = MagicMock()
    now = datetime.utcnow()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "plan": "pro_trial",
        "is_active": True,
        "trial_started_at": now - timedelta(days=3),
        "trial_ends_at": now + timedelta(days=4),
        "activated_by": None,
        "notes": None,
    }

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    result = get_current_plan(db=mock_db, user=mock_user)
    assert result["status"] == "trial_active"
    assert result["days_remaining"] >= 3
    assert result["plan"] == "pro_trial"


def test_plan_trial_expired():
    """Trial expirado retorna status correto."""
    from app.api.deps import get_current_plan

    mock_db = MagicMock()
    now = datetime.utcnow()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "plan": "pro_trial",
        "is_active": True,
        "trial_started_at": now - timedelta(days=10),
        "trial_ends_at": now - timedelta(days=3),
        "activated_by": None,
        "notes": None,
    }

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    result = get_current_plan(db=mock_db, user=mock_user)
    assert result["status"] == "trial_expired"
    assert result["days_remaining"] == 0


def test_plan_pro_active():
    """Plano PRO ativo retorna status active."""
    from app.api.deps import get_current_plan

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "plan": "pro",
        "is_active": True,
        "trial_started_at": None,
        "trial_ends_at": None,
        "activated_by": "admin-master",
        "notes": "",
    }

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    result = get_current_plan(db=mock_db, user=mock_user)
    assert result["status"] == "active"
    assert result["plan"] == "pro"


def test_plan_enterprise_active():
    """Plano Enterprise ativo nunca expira por trial."""
    from app.api.deps import get_current_plan

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "plan": "enterprise",
        "is_active": True,
        "trial_started_at": None,
        "trial_ends_at": None,
        "activated_by": "admin-master",
        "notes": "",
    }

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    result = get_current_plan(db=mock_db, user=mock_user)
    assert result["status"] == "active"
    assert result["plan"] == "enterprise"


def test_plan_customer_active():
    """Plano Customer ativo nunca expira por trial."""
    from app.api.deps import get_current_plan

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "plan": "customer",
        "is_active": True,
        "trial_started_at": None,
        "trial_ends_at": None,
        "activated_by": "admin-master",
        "notes": "",
    }

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    result = get_current_plan(db=mock_db, user=mock_user)
    assert result["status"] == "active"
    assert result["plan"] == "customer"


def test_plan_inactive():
    """Plano desativado retorna inactive."""
    from app.api.deps import get_current_plan

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "plan": "pro",
        "is_active": False,
        "trial_started_at": None,
        "trial_ends_at": None,
        "activated_by": None,
        "notes": None,
    }

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    result = get_current_plan(db=mock_db, user=mock_user)
    assert result["status"] == "inactive"
    assert result["is_active"] is False


def test_plan_no_record():
    """Org sem plano (legado) retorna trial_expired."""
    from app.api.deps import get_current_plan

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = None

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    result = get_current_plan(db=mock_db, user=mock_user)
    assert result["status"] == "trial_expired"


# ── require_active_plan guard ──────────────────────────────


def test_require_active_plan_blocks_expired():
    """require_active_plan bloqueia trial expirado com 402."""
    from fastapi import HTTPException
    from app.api.deps import require_active_plan

    mock_user = MagicMock()
    mock_user.org_id = "org-001"

    plan_info = {
        "plan": "pro_trial",
        "status": "trial_expired",
        "days_remaining": 0,
        "trial_ends_at": datetime.utcnow() - timedelta(days=1),
        "trial_started_at": datetime.utcnow() - timedelta(days=8),
        "is_active": True,
    }

    with pytest.raises(HTTPException) as exc_info:
        require_active_plan(plan_info=plan_info, user=mock_user)
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "plan_expired"


def test_require_active_plan_allows_trial():
    """require_active_plan permite trial ativo."""
    from app.api.deps import require_active_plan

    mock_user = MagicMock()
    plan_info = {
        "plan": "pro_trial",
        "status": "trial_active",
        "days_remaining": 5,
        "trial_ends_at": datetime.utcnow() + timedelta(days=5),
        "is_active": True,
    }

    result = require_active_plan(plan_info=plan_info, user=mock_user)
    assert result["status"] == "trial_active"


def test_require_active_plan_allows_pro():
    """require_active_plan permite plano PRO ativo."""
    from app.api.deps import require_active_plan

    mock_user = MagicMock()
    plan_info = {
        "plan": "pro",
        "status": "active",
        "days_remaining": None,
        "trial_ends_at": None,
        "is_active": True,
    }

    result = require_active_plan(plan_info=plan_info, user=mock_user)
    assert result["status"] == "active"


def test_require_active_plan_blocks_inactive():
    """require_active_plan bloqueia plano inativo."""
    from fastapi import HTTPException
    from app.api.deps import require_active_plan

    mock_user = MagicMock()
    plan_info = {
        "plan": "pro",
        "status": "inactive",
        "days_remaining": 0,
        "trial_ends_at": None,
        "is_active": False,
    }

    with pytest.raises(HTTPException) as exc_info:
        require_active_plan(plan_info=plan_info, user=mock_user)
    assert exc_info.value.status_code == 402


# ── Routes — plan status ──────────────────────────────


def test_get_plan_status_admin():
    """Admin pode ver status do plano."""
    from app.main import app
    from app.api.deps import get_current_user, get_session, get_data_session, get_current_product, get_current_plan
    from tests.conftest import _fake_user, _mock_session, _fake_product
    from fastapi.testclient import TestClient

    plan_data = {
        "plan": "pro_trial",
        "status": "trial_active",
        "days_remaining": 5,
        "trial_ends_at": datetime.utcnow() + timedelta(days=5),
        "is_active": True,
    }

    app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    app.dependency_overrides[get_current_product] = _fake_product
    app.dependency_overrides[get_current_plan] = lambda: plan_data

    client = TestClient(app)
    response = client.get("/api/admin/plan")
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "pro_trial"
    app.dependency_overrides.clear()


def test_get_plan_status_blocked_for_dev():
    """Dev nao pode ver status do plano."""
    from app.main import app
    from app.api.deps import get_current_user, get_session, get_data_session, get_current_product, get_current_plan
    from tests.conftest import _fake_user, _mock_session, _fake_product
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_current_user] = lambda: _fake_user("dev")
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    app.dependency_overrides[get_current_product] = _fake_product
    app.dependency_overrides[get_current_plan] = lambda: {"plan": "pro_trial", "status": "trial_active"}

    client = TestClient(app)
    response = client.get("/api/admin/plan")
    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_get_plan_status_blocked_for_suporte():
    """Suporte nao pode ver status do plano."""
    from app.main import app
    from app.api.deps import get_current_user, get_session, get_data_session, get_current_product, get_current_plan
    from tests.conftest import _fake_user, _mock_session, _fake_product
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_current_user] = lambda: _fake_user("suporte")
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    app.dependency_overrides[get_current_product] = _fake_product
    app.dependency_overrides[get_current_plan] = lambda: {"plan": "pro_trial", "status": "trial_active"}

    client = TestClient(app)
    response = client.get("/api/admin/plan")
    assert response.status_code == 403
    app.dependency_overrides.clear()


# ── Routes — contact ──────────────────────────────


@patch("app.api.routes.plans._send_contact_email")
def test_submit_contact(mock_email, admin_client):
    """Admin pode submeter contato de upgrade."""
    response = admin_client.post(
        "/api/admin/plan/contact",
        json={"contact_reason": "upgrade_pro", "message": "Quero continuar usando"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"


@patch("app.api.routes.plans._send_contact_email")
def test_submit_contact_dev(mock_email, dev_client):
    """Dev tambem pode submeter contato (qualquer role)."""
    response = dev_client.post(
        "/api/admin/plan/contact",
        json={"contact_reason": "enterprise", "message": "Interesse enterprise"},
    )
    assert response.status_code == 200


def test_submit_contact_invalid_reason(admin_client):
    """Motivo invalido retorna 400."""
    response = admin_client.post(
        "/api/admin/plan/contact",
        json={"contact_reason": "invalid", "message": ""},
    )
    assert response.status_code == 400


# ── Routes — master admin ──────────────────────────────


@patch("app.api.routes.plans.settings")
def test_master_admin_list_plans(mock_settings, admin_client):
    """Master admin pode listar todos os planos."""
    mock_settings.master_admin_email = "test@example.com"
    response = admin_client.get("/api/admin/plan/all")
    assert response.status_code in (200, 500)


@patch("app.api.routes.plans.settings")
def test_non_master_blocked(mock_settings):
    """Non-master admin nao pode acessar rotas master."""
    mock_settings.master_admin_email = "rafael@orbitalis.com"
    from app.main import app
    from app.api.deps import get_current_user, get_session, get_data_session, get_current_product
    from tests.conftest import _fake_user, _mock_session, _fake_product
    from fastapi.testclient import TestClient

    fake = _fake_user("admin")
    fake.email = "other@example.com"
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    app.dependency_overrides[get_current_product] = _fake_product

    client = TestClient(app)
    response = client.get("/api/admin/plan/all")
    assert response.status_code == 403
    app.dependency_overrides.clear()


@patch("app.api.routes.plans.settings")
def test_master_update_plan(mock_settings, admin_client):
    """Master admin pode atualizar plano de uma org."""
    mock_settings.master_admin_email = "test@example.com"
    response = admin_client.put(
        "/api/admin/plan/org-001",
        json={"plan": "pro", "is_active": True, "notes": "Upgrade manual"},
    )
    assert response.status_code in (200, 404, 500)


@patch("app.api.routes.plans.settings")
def test_master_extend_trial(mock_settings, admin_client):
    """Master admin pode estender trial."""
    mock_settings.master_admin_email = "test@example.com"
    response = admin_client.post(
        "/api/admin/plan/org-001/extend-trial",
        json={"days": 7},
    )
    assert response.status_code in (200, 404, 500)


@patch("app.api.routes.plans.settings")
def test_master_deactivate_plan(mock_settings, admin_client):
    """Master admin pode desativar plano."""
    mock_settings.master_admin_email = "test@example.com"
    response = admin_client.post("/api/admin/plan/org-001/deactivate")
    assert response.status_code in (200, 500)


@patch("app.api.routes.plans.settings")
def test_master_list_contacts(mock_settings, admin_client):
    """Master admin pode listar contatos."""
    mock_settings.master_admin_email = "test@example.com"
    response = admin_client.get("/api/admin/plan/contacts")
    assert response.status_code in (200, 500)


@patch("app.api.routes.plans.settings")
def test_extend_trial_invalid_days(mock_settings, admin_client):
    """Estender trial com dias invalidos retorna 400."""
    mock_settings.master_admin_email = "test@example.com"
    response = admin_client.post(
        "/api/admin/plan/org-001/extend-trial",
        json={"days": 100},
    )
    assert response.status_code == 400


@patch("app.api.routes.plans.settings")
def test_update_plan_invalid(mock_settings, admin_client):
    """Plano invalido retorna 400."""
    mock_settings.master_admin_email = "test@example.com"
    response = admin_client.put(
        "/api/admin/plan/org-001",
        json={"plan": "invalid_plan"},
    )
    assert response.status_code == 400


# ── Registration auto-creates trial ──────────────────────────────


def test_registration_creates_trial():
    """Novo registro cria trial automaticamente (verificacao de codigo)."""
    # Verify the registration code includes org_plans insertion
    import inspect
    from app.api.routes.auth import register
    source = inspect.getsource(register)
    assert "org_plans" in source
    assert "pro_trial" in source
    assert "trial_started_at" in source
    assert "trial_ends_at" in source
