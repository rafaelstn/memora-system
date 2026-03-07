from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class CodeGeneration(Base):
    __tablename__ = "code_generations"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    request_description = Column(Text, nullable=False)
    request_type = Column(String(50), nullable=False)
    file_path = Column(String(1024), nullable=True)
    use_context = Column(Boolean, default=True)
    context_used = Column(JSONB, nullable=True)
    generated_code = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())


class McpToken(Base):
    __tablename__ = "mcp_tokens"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    revoked_at = Column(DateTime, nullable=True)
