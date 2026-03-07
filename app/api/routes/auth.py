import re
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.config import settings
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
    onboarding_completed: bool = True
    onboarding_step: int = 0


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
    onboarding_completed = True
    onboarding_step = 0
    if db:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_name = org.name
            onboarding_completed = org.onboarding_completed
            onboarding_step = org.onboarding_step
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
        "onboarding_completed": onboarding_completed,
        "onboarding_step": onboarding_step,
    }


# --- Routes ---

@router.post("/auth/register", response_model=UserResponse)
def register(body: RegisterRequest, db: Session = Depends(get_session)):
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
    db.commit()

    return _user_response(user, db)


# Alias para compatibilidade
@router.post("/auth/setup", response_model=UserResponse)
def setup_alias(body: RegisterRequest, db: Session = Depends(get_session)):
    """Alias de /auth/register para compatibilidade."""
    return register(body, db)


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return _user_response(user, db)
