"""Rotas de preferencias de notificacao e configuracao SMTP."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_role
from app.models.user import User

router = APIRouter(prefix="/notifications")


class NotificationPrefs(BaseModel):
    email_enabled: bool = True
    alert_email: bool = True
    incident_email: bool = True
    review_email: bool = True
    security_email: bool = True
    executive_email: bool = True


@router.get("/preferences")
def get_preferences(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get current user's notification preferences."""
    row = db.execute(
        text("SELECT * FROM notification_preferences WHERE user_id = :uid"),
        {"uid": user.id},
    ).mappings().first()

    if not row:
        # Return defaults
        return {
            "email_enabled": True,
            "alert_email": True,
            "incident_email": True,
            "review_email": True,
            "security_email": True,
            "executive_email": True,
        }
    return dict(row)


@router.put("/preferences")
def update_preferences(
    prefs: NotificationPrefs,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Update current user's notification preferences."""
    existing = db.execute(
        text("SELECT id FROM notification_preferences WHERE user_id = :uid"),
        {"uid": user.id},
    ).mappings().first()

    if existing:
        db.execute(
            text("""
                UPDATE notification_preferences SET
                    email_enabled = :email_enabled,
                    alert_email = :alert_email,
                    incident_email = :incident_email,
                    review_email = :review_email,
                    security_email = :security_email,
                    executive_email = :executive_email,
                    updated_at = now()
                WHERE user_id = :uid
            """),
            {"uid": user.id, **prefs.model_dump()},
        )
    else:
        db.execute(
            text("""
                INSERT INTO notification_preferences
                    (user_id, email_enabled, alert_email, incident_email,
                     review_email, security_email, executive_email)
                VALUES (:uid, :email_enabled, :alert_email, :incident_email,
                        :review_email, :security_email, :executive_email)
            """),
            {"uid": user.id, **prefs.model_dump()},
        )
    db.commit()
    return prefs.model_dump()


# --- SMTP Config (admin only) ---

class SMTPConfig(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_from: str


@router.get("/smtp")
def get_smtp_config(
    user: User = Depends(require_role("admin")),
):
    """Get current SMTP configuration (masked)."""
    from app.config import settings
    return {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user,
        "smtp_password": "••••••••" if settings.smtp_password else "",
        "smtp_from": settings.smtp_from or settings.smtp_user,
        "configured": bool(settings.smtp_host and settings.smtp_user),
    }


@router.post("/smtp/test")
def test_smtp(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Send a test email to the current admin."""
    from app.core.email_client import send_test_email
    success = send_test_email(user.email)
    if success:
        return {"status": "ok", "message": f"Email de teste enviado para {user.email}"}
    raise HTTPException(500, "Falha ao enviar email de teste. Verifique a configuracao SMTP.")
