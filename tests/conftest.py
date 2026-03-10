from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_product, get_current_user, get_data_session, get_session
from app.main import app
from app.models.product import Product
from app.models.user import User


def _fake_user(role: str = "admin") -> User:
    user = MagicMock(spec=User)
    user.id = "u-test-001"
    user.name = "Test User"
    user.email = "test@example.com"
    user.role = role
    user.avatar_url = None
    user.is_active = True
    user.github_connected = False
    user.org_id = "org-test-001"
    return user


def _fake_product() -> Product:
    product = MagicMock(spec=Product)
    product.id = "prod-test-001"
    product.org_id = "org-test-001"
    product.name = "Produto Principal"
    product.description = "Produto padrao de teste"
    product.is_active = True
    return product


def _mock_session() -> MagicMock:
    """Mock DB session with safe defaults for ORM queries."""
    session = MagicMock()
    # Default: query().filter().first() returns None (avoids MagicMock leaking into Pydantic)
    session.query.return_value.filter.return_value.first.return_value = None
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


@pytest.fixture()
def anon_client():
    app.dependency_overrides.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
