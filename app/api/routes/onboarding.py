from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.models.organization import Organization
from app.models.user import User

router = APIRouter()


class OnboardingUpdateRequest(BaseModel):
    step: int
    completed: bool = False


class OnboardingStatusResponse(BaseModel):
    onboarding_completed: bool
    onboarding_step: int
    onboarding_completed_at: str | None = None


class OrgNameUpdateRequest(BaseModel):
    name: str
    app_url: str | None = None


@router.get("/organizations/onboarding")
def get_onboarding_status(
    user: User = Depends(require_role("admin", "dev", "suporte")),
    db: Session = Depends(get_session),
):
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organizacao nao encontrada")
    return {
        "onboarding_completed": org.onboarding_completed,
        "onboarding_step": org.onboarding_step,
        "onboarding_completed_at": str(org.onboarding_completed_at) if org.onboarding_completed_at else None,
    }


@router.patch("/organizations/onboarding")
def update_onboarding(
    body: OnboardingUpdateRequest,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_session),
):
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organizacao nao encontrada")

    org.onboarding_step = body.step

    if body.completed:
        org.onboarding_completed = True
        org.onboarding_completed_at = datetime.utcnow()

    db.commit()

    return {
        "onboarding_completed": org.onboarding_completed,
        "onboarding_step": org.onboarding_step,
        "onboarding_completed_at": str(org.onboarding_completed_at) if org.onboarding_completed_at else None,
    }


@router.patch("/organizations/name")
def update_org_name(
    body: OrgNameUpdateRequest,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_session),
):
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organizacao nao encontrada")

    org.name = body.name
    if body.app_url is not None:
        settings = org.settings or {}
        settings["app_url"] = body.app_url
        org.settings = settings

    db.commit()

    return {"name": org.name, "app_url": (org.settings or {}).get("app_url")}
