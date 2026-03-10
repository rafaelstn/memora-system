import re
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.config import settings
from app.core.rate_limit import AUTH_LIMIT, REGISTER_LIMIT, limiter
from app.core.refresh_tokens import (
    revoke_token as revoke_refresh_token,
    validate_and_rotate,
)
from app.models.organization import Organization
from app.models.user import User

router = APIRouter()


# --- Schemas ---

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    org_name: str | None = None
    invite_token: str | None = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    avatar_url: str | None
    is_active: bool
    github_connected: bool
    org_id: str
    org_name: str | None = None
    org_mode: str = "saas"
    enterprise_setup_complete: bool = True
    onboarding_completed: bool = True
    onboarding_step: int = 0
    created_at: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class AdminExistsResponse(BaseModel):
    exists: bool
    total_users: int
    requires_invite: bool


# --- Helpers ---

def _supabase_admin_headers() -> dict:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _create_supabase_user(email: str, password: str) -> str:
    """Cria usuario no Supabase Auth e retorna o user ID."""
    url = f"{settings.supabase_url}/auth/v1/admin/users"
    resp = httpx.post(
        url,
        headers=_supabase_admin_headers(),
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
        },
        timeout=10,
    )
    if resp.status_code == 422:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado no Supabase Auth")
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao criar usuário no Supabase Auth: {resp.text}",
        )
    return resp.json()["id"]


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:100]


def _user_response(user: User, db: Session | None = None) -> dict:
    org_name = None
    org_mode = "saas"
    enterprise_setup_complete = True
    onboarding_completed = True
    onboarding_step = 0
    if db:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_name = org.name
            org_mode = getattr(org, "mode", "saas") or "saas"
            onboarding_completed = org.onboarding_completed
            onboarding_step = org.onboarding_step
        # Verificar setup Enterprise se aplicavel
        if org_mode == "enterprise":
            from sqlalchemy import text
            row = db.execute(
                text("SELECT setup_complete FROM enterprise_db_configs WHERE org_id = :org_id"),
                {"org_id": user.org_id},
            ).first()
            enterprise_setup_complete = bool(row and row[0])
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "github_connected": user.github_connected,
        "org_id": user.org_id,
        "org_name": org_name,
        "org_mode": org_mode,
        "enterprise_setup_complete": enterprise_setup_complete,
        "onboarding_completed": onboarding_completed,
        "onboarding_step": onboarding_step,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# --- Routes ---

@router.post("/auth/register", response_model=UserResponse)
@limiter.limit(REGISTER_LIMIT)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_session)):
    """Cadastro unificado: primeiro usuario cria org e vira admin, demais precisam de convite."""
    total_users = db.query(User).count()

    # Check duplicate email
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")

    if total_users == 0 or (body.org_name and not body.invite_token):
        # Novo cadastro — cria organização + admin
        org_name = body.org_name or body.name
        base_slug = _slugify(org_name)
        slug = base_slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(
            id=str(uuid.uuid4()),
            name=org_name,
            slug=slug,
        )
        db.add(org)
        db.flush()

        supabase_uid = _create_supabase_user(body.email, body.password)
        user = User(
            id=supabase_uid,
            org_id=org.id,
            name=body.name,
            email=body.email,
            role="admin",
            is_active=True,
            github_connected=False,
        )
        db.add(user)

        # Auto-create trial plan for new org
        from datetime import datetime, timedelta
        plan_id = str(uuid.uuid4())
        now = datetime.utcnow()
        db.execute(
            text("""
                INSERT INTO org_plans (id, org_id, plan, trial_started_at, trial_ends_at, is_active)
                VALUES (:id, :org_id, 'pro_trial', :started, :ends, true)
            """),
            {
                "id": plan_id,
                "org_id": org.id,
                "started": now,
                "ends": now + timedelta(days=7),
            },
        )

        db.commit()
        return _user_response(user, db)

    # Sistema ja tem usuarios — exige convite
    if not body.invite_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro restrito. Solicite um convite ao administrador.",
        )

    invite = db.execute(
        text("""
            SELECT * FROM invites
            WHERE token = :token AND status = 'pending' AND expires_at > now()
        """),
        {"token": body.invite_token},
    ).mappings().first()

    if not invite:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Convite inválido ou expirado")

    if invite["email"] and invite["email"] != body.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email não corresponde ao convite")

    supabase_uid = _create_supabase_user(body.email, body.password)

    user = User(
        id=supabase_uid,
        org_id=invite["org_id"],
        name=body.name,
        email=body.email,
        role=invite["role"],
        invited_by=invite.get("created_by"),
        is_active=True,
        github_connected=False,
    )
    db.add(user)

    db.execute(
        text("UPDATE invites SET status = 'used', used_by = :uid WHERE id = :iid"),
        {"uid": supabase_uid, "iid": invite["id"]},
    )

    # Auto-create product membership if invite has product_id
    invite_product_id = invite.get("product_id")
    if invite_product_id:
        membership_id = str(uuid.uuid4())
        db.execute(
            text("""
                INSERT INTO product_memberships (id, product_id, user_id)
                VALUES (:id, :product_id, :user_id)
                ON CONFLICT (product_id, user_id) DO NOTHING
            """),
            {"id": membership_id, "product_id": invite_product_id, "user_id": supabase_uid},
        )

    db.commit()

    return _user_response(user, db)


# Alias para compatibilidade
@router.post("/auth/setup", response_model=UserResponse)
@limiter.limit(REGISTER_LIMIT)
def setup_alias(request: Request, body: RegisterRequest, db: Session = Depends(get_session)):
    """Alias de /auth/register para compatibilidade."""
    return register(request, body, db)


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return _user_response(user, db)


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


class ChangePasswordRequest(BaseModel):
    new_password: str


@router.patch("/auth/profile", response_model=UserResponse)
def update_profile(body: UpdateProfileRequest, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """Atualiza nome e/ou avatar do usuário logado."""
    updates = {}
    if body.name is not None:
        name = body.name.strip()
        if not name or len(name) > 255:
            raise HTTPException(status_code=400, detail="Nome inválido")
        updates["name"] = name
    if body.avatar_url is not None:
        if body.avatar_url and len(body.avatar_url) > 1024:
            raise HTTPException(status_code=400, detail="URL do avatar muito longa")
        updates["avatar_url"] = body.avatar_url or None

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["uid"] = user.id
    db.execute(text(f"UPDATE users SET {set_clauses}, updated_at = now() WHERE id = :uid"), updates)
    db.commit()
    db.refresh(user)
    return _user_response(user, db)


@router.post("/auth/change-password")
@limiter.limit(AUTH_LIMIT)
def change_password(request: Request, body: ChangePasswordRequest, user: User = Depends(get_current_user)):
    """Altera a senha do usuário via Supabase Admin API."""
    password = body.new_password
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")

    url = f"{settings.supabase_url}/auth/v1/admin/users/{user.id}"
    resp = httpx.put(
        url,
        headers=_supabase_admin_headers(),
        json={"password": password},
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Erro ao atualizar senha no Supabase Auth")

    return {"message": "Senha alterada com sucesso"}


@router.post("/auth/refresh")
@limiter.limit(AUTH_LIMIT)
def refresh_token(request: Request, body: RefreshRequest, db: Session = Depends(get_session)):
    """Troca refresh token por novo access token + novo refresh token (rotacao)."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        new_token, user_id = validate_and_rotate(db, body.refresh_token, ip_address, user_agent)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida. Faça login novamente.",
        )

    return {"refresh_token": new_token, "message": "Token renovado com sucesso"}


@router.post("/auth/logout")
def logout(body: RefreshRequest, db: Session = Depends(get_session)):
    """Revoga o refresh token atual (logout)."""
    revoke_refresh_token(db, body.refresh_token)
    return {"message": "Logout realizado com sucesso"}
