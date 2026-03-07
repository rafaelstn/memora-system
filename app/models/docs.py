from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class RepoDoc(Base):
    __tablename__ = "repo_docs"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    doc_type = Column(String(20), nullable=False, index=True)  # readme | onboarding_guide
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    generation_trigger = Column(String(20), nullable=False, default="manual")  # push | manual
    pushed_to_github = Column(Boolean, nullable=False, default=False)
    pushed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<RepoDoc {self.doc_type}:{self.repo_name}>"


class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    guide_id = Column(String(36), ForeignKey("repo_docs.id"), nullable=False)
    steps_total = Column(Integer, nullable=False, default=0)
    steps_completed = Column(Integer, nullable=False, default=0)
    completed_steps = Column(JSONB, nullable=False, default=list)
    started_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<OnboardingProgress {self.user_id}:{self.repo_name}>"
