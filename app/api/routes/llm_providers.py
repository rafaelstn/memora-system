import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.core.encryption import encrypt_api_key, mask_api_key, decrypt_api_key
from app.integrations.llm_clients.pricing import PROVIDER_MODELS
from app.integrations.llm_router import test_provider, test_connection_raw
from app.models.user import User

router = APIRouter(
    prefix="/llm-providers",
    dependencies=[Depends(require_role("admin"))],
)


class CreateProviderRequest(BaseModel):
    name: str
    provider: str
    model_id: str
    api_key: str | None = None
    base_url: str | None = None


class UpdateProviderRequest(BaseModel):
    name: str | None = None
    model_id: str | None = None
    api_key: str | None = None
    base_url: str | None = None


def _provider_to_dict(row: dict) -> dict:
    """Convert a DB row to a safe dict (never expose full api_key)."""
    api_key_masked = ""
    if row.get("api_key_encrypted"):
        try:
            plain = decrypt_api_key(row["api_key_encrypted"])
            api_key_masked = mask_api_key(plain)
        except Exception:
            api_key_masked = "***erro***"

    return {
        "id": row["id"],
        "name": row["name"],
        "provider": row["provider"],
        "model_id": row["model_id"],
        "api_key_masked": api_key_masked,
        "base_url": row.get("base_url"),
        "is_active": row["is_active"],
        "is_default": row["is_default"],
        "last_tested_at": str(row["last_tested_at"]) if row.get("last_tested_at") else None,
        "last_test_status": row["last_test_status"],
        "last_test_error": row.get("last_test_error"),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


@router.get("")
def list_providers(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    rows = db.execute(
        text("""
            SELECT * FROM llm_providers
            WHERE org_id = :org_id AND is_active = true
            ORDER BY is_default DESC, created_at ASC
        """),
        {"org_id": user.org_id},
    ).mappings().all()
    return [_provider_to_dict(dict(r)) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_provider(
    body: CreateProviderRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    # Validate provider type
    if body.provider not in PROVIDER_MODELS:
        raise HTTPException(400, f"Provedor invalido: {body.provider}")

    # Validate model_id (ollama accepts anything)
    if body.provider != "ollama" and PROVIDER_MODELS[body.provider]:
        if body.model_id not in PROVIDER_MODELS[body.provider]:
            raise HTTPException(
                400,
                f"Modelo {body.model_id} nao suportado para {body.provider}. "
                f"Disponiveis: {', '.join(PROVIDER_MODELS[body.provider])}",
            )

    # API key required for non-ollama
    if body.provider != "ollama" and not body.api_key:
        raise HTTPException(400, f"API key obrigatoria para provedor {body.provider}")

    encrypted_key = encrypt_api_key(body.api_key) if body.api_key else None
    provider_id = str(uuid.uuid4())

    try:
        # Check if this is the first provider (auto-set as default)
        count = db.execute(
            text("SELECT COUNT(*) FROM llm_providers WHERE org_id = :org_id AND is_active = true"),
            {"org_id": user.org_id},
        ).scalar()
        is_default = count == 0

        db.execute(
            text("""
                INSERT INTO llm_providers
                    (id, org_id, name, provider, model_id, api_key_encrypted, base_url, is_default, added_by)
                VALUES
                    (:id, :org_id, :name, :provider, :model_id, :api_key_encrypted, :base_url, :is_default, :added_by)
            """),
            {
                "id": provider_id,
                "org_id": user.org_id,
                "name": body.name,
                "provider": body.provider,
                "model_id": body.model_id,
                "api_key_encrypted": encrypted_key,
                "base_url": body.base_url,
                "is_default": is_default,
                "added_by": user.id,
            },
        )
        db.commit()
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if "llm_providers" in error_msg and ("does not exist" in error_msg or "not exist" in error_msg):
            raise HTTPException(
                500,
                "Tabela llm_providers nao existe. Execute: python scripts/migrate_add_llm_providers.py",
            )
        raise HTTPException(500, f"Erro ao salvar provedor: {error_msg[:200]}")

    row = db.execute(
        text("SELECT * FROM llm_providers WHERE id = :id"),
        {"id": provider_id},
    ).mappings().first()
    return _provider_to_dict(dict(row))


class TestConnectionRequest(BaseModel):
    provider: str
    model_id: str
    api_key: str | None = None
    base_url: str | None = None


@router.post("/test-connection")
def test_connection_endpoint(
    body: TestConnectionRequest,
    user: User = Depends(require_role("admin")),
):
    """Test LLM connection with raw credentials — no DB required."""
    if body.provider not in PROVIDER_MODELS:
        raise HTTPException(400, f"Provedor invalido: {body.provider}")
    if body.provider != "ollama" and not body.api_key:
        raise HTTPException(400, f"API key obrigatoria para provedor {body.provider}")

    return test_connection_raw(
        provider=body.provider,
        model_id=body.model_id,
        api_key=body.api_key,
        base_url=body.base_url,
    )


@router.put("/{provider_id}")
def update_provider(
    provider_id: str,
    body: UpdateProviderRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    row = db.execute(
        text("SELECT * FROM llm_providers WHERE id = :id AND org_id = :org_id AND is_active = true"),
        {"id": provider_id, "org_id": user.org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Provedor nao encontrado")

    updates = []
    params: dict = {"id": provider_id}

    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.model_id is not None:
        updates.append("model_id = :model_id")
        params["model_id"] = body.model_id
    if body.api_key is not None:
        updates.append("api_key_encrypted = :api_key_encrypted")
        params["api_key_encrypted"] = encrypt_api_key(body.api_key)
    if body.base_url is not None:
        updates.append("base_url = :base_url")
        params["base_url"] = body.base_url

    if updates:
        updates.append("updated_at = NOW()")
        from app.core.query_builder import build_set_clause
        set_clause = build_set_clause("llm_providers", updates)
        db.execute(
            text(f"UPDATE llm_providers SET {set_clause} WHERE id = :id"),
            params,
        )
        db.commit()

    updated = db.execute(
        text("SELECT * FROM llm_providers WHERE id = :id"),
        {"id": provider_id},
    ).mappings().first()
    return _provider_to_dict(dict(updated))


@router.delete("/{provider_id}")
def delete_provider(
    provider_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    row = db.execute(
        text("SELECT * FROM llm_providers WHERE id = :id AND org_id = :org_id AND is_active = true"),
        {"id": provider_id, "org_id": user.org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Provedor nao encontrado")

    if row["is_default"]:
        raise HTTPException(400, "Defina outro modelo padrao antes de remover este provedor")

    db.execute(
        text("UPDATE llm_providers SET is_active = false, updated_at = NOW() WHERE id = :id"),
        {"id": provider_id},
    )
    db.commit()
    return {"deleted": True}


@router.post("/{provider_id}/set-default")
def set_default(
    provider_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    row = db.execute(
        text("SELECT * FROM llm_providers WHERE id = :id AND org_id = :org_id AND is_active = true"),
        {"id": provider_id, "org_id": user.org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Provedor nao encontrado")

    # Remove default from all others
    db.execute(
        text("UPDATE llm_providers SET is_default = false WHERE org_id = :org_id"),
        {"org_id": user.org_id},
    )
    # Set new default
    db.execute(
        text("UPDATE llm_providers SET is_default = true, updated_at = NOW() WHERE id = :id"),
        {"id": provider_id},
    )
    db.commit()
    return {"default": True, "provider_id": provider_id}


@router.post("/{provider_id}/test")
def test_provider_endpoint(
    provider_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    # Verify ownership
    row = db.execute(
        text("SELECT id FROM llm_providers WHERE id = :id AND org_id = :org_id AND is_active = true"),
        {"id": provider_id, "org_id": user.org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Provedor nao encontrado")

    return test_provider(db, provider_id, user.org_id)


# Public endpoint for listing active providers (for model selector in chat)
# Any authenticated user can see the list (but not API keys)
active_router = APIRouter(prefix="/llm-providers")


@active_router.get("/active")
def list_active_providers(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev", "suporte")),
):
    """List active providers for model selector. No sensitive data exposed."""
    rows = db.execute(
        text("""
            SELECT id, name, provider, model_id, is_default, last_test_status
            FROM llm_providers
            WHERE org_id = :org_id AND is_active = true
            ORDER BY is_default DESC, name ASC
        """),
        {"org_id": user.org_id},
    ).mappings().all()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "provider": r["provider"],
            "model_id": r["model_id"],
            "is_default": r["is_default"],
            "last_test_status": r["last_test_status"],
        }
        for r in rows
    ]
