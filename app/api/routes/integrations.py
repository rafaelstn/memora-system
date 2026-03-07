import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.models.github_integration import GitHubIntegration
from app.models.user import User

router = APIRouter(
    prefix="/integrations",
    dependencies=[Depends(require_role("admin"))],
)


class ConnectGitHubRequest(BaseModel):
    token: str


class GitHubStatusResponse(BaseModel):
    connected: bool
    github_login: str | None = None
    github_avatar_url: str | None = None
    scopes: str | None = None
    connected_at: str | None = None


@router.post("/github")
def connect_github(
    body: ConnectGitHubRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Valida e salva o Personal Access Token do GitHub."""
    try:
        resp = httpx.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {body.token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível conectar ao GitHub")

    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token GitHub inválido")

    gh_user = resp.json()
    scopes = resp.headers.get("x-oauth-scopes", "")

    # Deactivate previous integrations for this org
    db.query(GitHubIntegration).filter(
        GitHubIntegration.org_id == user.org_id,
        GitHubIntegration.is_active.is_(True),
    ).update({"is_active": False})

    integration = GitHubIntegration(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        installed_by=user.id,
        github_token=body.token,
        github_login=gh_user["login"],
        github_avatar_url=gh_user.get("avatar_url"),
        scopes=scopes,
        is_active=True,
    )
    db.add(integration)

    user.github_connected = True
    db.commit()

    return {
        "connected": True,
        "github_login": gh_user["login"],
        "github_avatar_url": gh_user.get("avatar_url"),
        "scopes": scopes,
    }


@router.get("/github", response_model=GitHubStatusResponse)
def get_github_status(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Retorna status da integração GitHub (nunca retorna o token)."""
    integration = (
        db.query(GitHubIntegration)
        .filter(GitHubIntegration.org_id == user.org_id, GitHubIntegration.is_active.is_(True))
        .first()
    )
    if not integration:
        return {"connected": False}

    return {
        "connected": True,
        "github_login": integration.github_login,
        "github_avatar_url": integration.github_avatar_url,
        "scopes": integration.scopes,
        "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
    }


@router.get("/github/repos")
def list_github_repos(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Lista repositórios disponíveis no GitHub."""
    integration = (
        db.query(GitHubIntegration)
        .filter(GitHubIntegration.org_id == user.org_id, GitHubIntegration.is_active.is_(True))
        .first()
    )
    if not integration:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub não conectado")

    repos = []
    page = 1
    while True:
        resp = httpx.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {integration.github_token}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": 100, "page": page, "sort": "updated"},
            timeout=15,
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        for r in data:
            repos.append({
                "name": r["name"],
                "full_name": r["full_name"],
                "private": r["private"],
                "url": r["html_url"],
                "language": r.get("language"),
                "updated_at": r.get("updated_at"),
                "default_branch": r.get("default_branch", "main"),
            })
        page += 1
        if len(data) < 100:
            break

    return repos


@router.delete("/github")
def disconnect_github(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Desativa a integração GitHub."""
    updated = (
        db.query(GitHubIntegration)
        .filter(GitHubIntegration.org_id == user.org_id, GitHubIntegration.is_active.is_(True))
        .update({"is_active": False})
    )
    if updated == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma integração ativa")

    user.github_connected = False
    db.commit()

    return {"connected": False, "message": "Integração GitHub desconectada"}
