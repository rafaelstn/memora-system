from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func, UniqueConstraint

from app.models.chunk import Base


class GitHubIntegration(Base):
    __tablename__ = "github_integration"

    __table_args__ = (UniqueConstraint("org_id", "is_active", name="uq_github_org_active"),)

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    installed_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    github_token = Column(Text, nullable=False)
    github_login = Column(String(255), nullable=False)
    github_avatar_url = Column(String(1024))
    scopes = Column(Text)
    connected_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    last_used_at = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<GitHubIntegration {self.github_login} active={self.is_active}>"
