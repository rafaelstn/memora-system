"""Testes para o modulo de Produtos (Org -> Produto)."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_product, get_current_user, get_data_session, get_session
from app.main import app
from app.models.product import Product
from app.models.user import User


# ---------- Helpers ----------


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
    product.description = "Produto padrao"
    product.is_active = True
    return product


def _mock_session() -> MagicMock:
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session


# ---------- Fixtures ----------


@pytest.fixture()
def admin_client():
    fake = _fake_user("admin")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def dev_client():
    fake = _fake_user("dev")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def suporte_client():
    fake = _fake_user("suporte")
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_data_session] = _mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- Testes: CRUD de Produtos ----------


class TestProductCRUD:
    """Testa operacoes CRUD de produtos."""

    def test_create_product_admin(self, admin_client):
        """Admin pode criar produto."""
        mock_db = _mock_session()
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.post("/api/products", json={
            "name": "Backend API",
            "description": "Servicos backend",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Backend API"
        assert data["description"] == "Servicos backend"
        assert data["org_id"] == "org-test-001"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_product_dev_forbidden(self, dev_client):
        """Dev nao pode criar produto."""
        resp = dev_client.post("/api/products", json={
            "name": "Tentativa",
        })
        assert resp.status_code == 403

    def test_create_product_suporte_forbidden(self, suporte_client):
        """Suporte nao pode criar produto."""
        resp = suporte_client.post("/api/products", json={
            "name": "Tentativa",
        })
        assert resp.status_code == 403

    def test_list_products_admin(self, admin_client):
        """Admin lista todos os produtos da org."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.all.return_value = [
            {
                "id": "prod-001",
                "org_id": "org-test-001",
                "name": "Backend",
                "description": None,
                "is_active": True,
                "member_count": 3,
                "created_at": "2026-01-01 00:00:00",
            }
        ]
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.get("/api/products")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Backend"
        assert data[0]["member_count"] == 3

    def test_list_products_dev_filtered(self, dev_client):
        """Dev lista apenas produtos que e membro."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.all.return_value = [
            {
                "id": "prod-001",
                "org_id": "org-test-001",
                "name": "Backend",
                "description": None,
                "is_active": True,
                "member_count": 2,
                "created_at": "2026-01-01 00:00:00",
            }
        ]
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = dev_client.get("/api/products")
        assert resp.status_code == 200
        # Query inclui INNER JOIN com product_memberships
        call_args = mock_db.execute.call_args
        sql = str(call_args[0][0].text)
        assert "product_memberships" in sql

    def test_archive_product_admin(self, admin_client):
        """Admin pode arquivar produto."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "id": "prod-001",
            "org_id": "org-test-001",
            "name": "Backend",
            "description": None,
            "is_active": True,
        }
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.delete("/api/products/prod-001")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Produto arquivado"

    def test_archive_product_dev_forbidden(self, dev_client):
        """Dev nao pode arquivar produto."""
        resp = dev_client.delete("/api/products/prod-001")
        assert resp.status_code == 403

    def test_update_product_admin(self, admin_client):
        """Admin pode atualizar produto."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "id": "prod-001",
            "org_id": "org-test-001",
            "name": "Backend Atualizado",
            "description": "Nova descricao",
            "is_active": True,
        }
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.put("/api/products/prod-001", json={
            "name": "Backend Atualizado",
            "description": "Nova descricao",
        })
        assert resp.status_code == 200

    def test_get_product_not_found(self, admin_client):
        """Retorna 404 para produto inexistente."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.get("/api/products/nao-existe")
        assert resp.status_code == 404


# ---------- Testes: Membros ----------


class TestProductMembership:
    """Testa operacoes de membros de produtos."""

    def test_add_member_admin(self, admin_client):
        """Admin pode adicionar membro."""
        mock_db = _mock_session()
        # Produto existe
        mock_db.execute.return_value.mappings.return_value.first.side_effect = [
            {"id": "prod-001", "org_id": "org-test-001", "name": "Backend", "description": None, "is_active": True},
            {"id": "u-002", "name": "Dev User", "email": "dev@test.com", "role": "dev"},
        ]
        # Membership nao existe ainda
        mock_db.execute.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.post("/api/products/prod-001/members", json={
            "user_id": "u-002",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["product_id"] == "prod-001"
        assert data["user_id"] == "u-002"

    def test_add_member_dev_forbidden(self, dev_client):
        """Dev nao pode adicionar membro."""
        resp = dev_client.post("/api/products/prod-001/members", json={
            "user_id": "u-002",
        })
        assert resp.status_code == 403

    def test_remove_member_admin(self, admin_client):
        """Admin pode remover membro."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "id": "prod-001", "org_id": "org-test-001", "name": "Backend",
            "description": None, "is_active": True,
        }
        mock_db.execute.return_value.rowcount = 1
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.delete("/api/products/prod-001/members/u-002")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Membro removido"

    def test_list_members_admin(self, admin_client):
        """Admin pode listar membros."""
        mock_db = _mock_session()
        # Primeiro call: produto existe; Segundo call: lista membros
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "id": "prod-001", "org_id": "org-test-001", "name": "Backend",
            "description": None, "is_active": True,
        }
        mock_db.execute.return_value.mappings.return_value.all.return_value = [
            {
                "id": "u-001", "name": "Admin", "email": "admin@test.com",
                "role": "admin", "avatar_url": None, "joined_at": "2026-01-01",
            },
            {
                "id": "u-002", "name": "Dev", "email": "dev@test.com",
                "role": "dev", "avatar_url": None, "joined_at": "2026-01-02",
            },
        ]
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.get("/api/products/prod-001/members")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


# ---------- Testes: Acesso por Produto ----------


class TestProductAccess:
    """Testa que admin acessa qualquer produto e dev/suporte so os seus."""

    def test_admin_accesses_any_product(self, admin_client):
        """Admin da org acessa qualquer produto."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.first.return_value = {
            "id": "prod-other",
            "org_id": "org-test-001",
            "name": "Outro Produto",
            "description": None,
            "is_active": True,
        }
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.get("/api/products/prod-other")
        assert resp.status_code == 200

    def test_dev_without_membership_blocked(self, dev_client):
        """Dev sem membership nao acessa produto."""
        mock_db = _mock_session()
        # Produto existe
        mock_db.execute.return_value.mappings.return_value.first.side_effect = [
            {"id": "prod-other", "org_id": "org-test-001", "name": "Outro", "description": None, "is_active": True},
        ]
        # Sem membership
        mock_db.execute.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = dev_client.get("/api/products/prod-other")
        assert resp.status_code == 403

    def test_repos_require_product_id(self, admin_client):
        """Endpoint /api/repos exige X-Product-ID."""
        mock_db = _mock_session()
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        # Sem header X-Product-ID
        resp = admin_client.get("/api/repos")
        assert resp.status_code == 400
        assert "Product ID" in resp.json()["detail"]

    def test_repos_with_product_id(self, admin_client):
        """Endpoint /api/repos funciona com X-Product-ID."""
        mock_db = _mock_session()
        mock_db.execute.return_value.mappings.return_value.all.return_value = []
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db
        app.dependency_overrides[get_current_product] = lambda: _fake_product()

        resp = admin_client.get("/api/repos")
        assert resp.status_code == 200

        app.dependency_overrides.pop(get_current_product, None)


# ---------- Testes: Guard get_current_product ----------


class TestGetCurrentProduct:
    """Testa a dependency get_current_product."""

    def test_missing_product_id_returns_400(self, admin_client):
        """Sem X-Product-ID nem query param retorna 400."""
        mock_db = _mock_session()
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.get("/api/repos")
        assert resp.status_code == 400

    def test_product_not_found_returns_404(self, admin_client):
        """Product ID invalido retorna 404."""
        mock_db = _mock_session()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        resp = admin_client.get("/api/repos", headers={"X-Product-ID": "nao-existe"})
        assert resp.status_code == 404

    def test_dev_not_member_returns_403(self):
        """Dev sem membership retorna 403."""
        mock_db = _mock_session()

        # Product exists
        product_mock = MagicMock(spec=Product)
        product_mock.id = "prod-001"
        product_mock.org_id = "org-test-001"
        product_mock.is_active = True

        # query(Product).filter().first() returns product
        # query(ProductMembership).filter().first() returns None
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            product_mock,  # Product found
            None,  # No membership
        ]

        fake = _fake_user("dev")
        app.dependency_overrides[get_current_user] = lambda: fake
        app.dependency_overrides[get_session] = lambda: mock_db
        app.dependency_overrides[get_data_session] = lambda: mock_db

        client = TestClient(app)
        resp = client.get("/api/repos", headers={"X-Product-ID": "prod-001"})
        assert resp.status_code == 403

        app.dependency_overrides.clear()
