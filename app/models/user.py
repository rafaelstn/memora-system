from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func

from app.models.chunk import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(20), nullable=False, default="suporte")
    avatar_url = Column(String(1024))
    is_active = Column(Boolean, default=True, nullable=False)
    invited_by = Column(String(36))
    github_connected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    last_activity = Column(DateTime)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
