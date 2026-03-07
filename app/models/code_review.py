from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class CodeReview(Base):
    __tablename__ = "code_reviews"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_id = Column(String(36))
    source_type = Column(String(20), nullable=False)  # pr | manual
    pr_number = Column(Integer)
    pr_title = Column(String(500))
    pr_url = Column(String(1024))
    pr_author = Column(String(255))
    submitted_by = Column(String(36), ForeignKey("users.id"))
    code_snippet = Column(Text)
    language = Column(String(50))
    diff = Column(Text)
    files_changed = Column(JSONB)
    status = Column(String(20), nullable=False, default="pending")  # pending | analyzing | completed | failed
    overall_score = Column(Integer)
    overall_verdict = Column(String(30))  # approved | approved_with_warnings | needs_changes | rejected
    summary = Column(Text)
    github_comment_id = Column(String(255))
    github_comment_posted = Column(Boolean, default=False, nullable=False)
    custom_instructions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __repr__(self):
        return f"<CodeReview {self.id}:{self.source_type}:{self.status}>"


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id = Column(String(36), primary_key=True)
    review_id = Column(String(36), ForeignKey("code_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    category = Column(String(20), nullable=False)  # bug | security | performance | consistency | pattern
    severity = Column(String(20), nullable=False)  # critical | high | medium | low | info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    suggestion = Column(Text)
    file_path = Column(String(1024))
    line_start = Column(Integer)
    line_end = Column(Integer)
    code_snippet = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    def __repr__(self):
        return f"<ReviewFinding {self.id}:{self.category}:{self.severity}>"
