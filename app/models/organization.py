from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    settings = Column(JSONB, default=dict)
    mode = Column(String(20), nullable=False, default="saas", server_default="saas")
    onboarding_completed = Column(Boolean, default=False, server_default="false", nullable=False)
    onboarding_step = Column(Integer, default=0, server_default="0", nullable=False)
    onboarding_completed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Organization {self.name} ({self.slug})>"
