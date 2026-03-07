from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func

from app.models.chunk import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(20), nullable=False)  # openai | anthropic | google | groq | ollama
    model_id = Column(String(255), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    base_url = Column(String(1024), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    added_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    last_tested_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=False, default="untested")  # ok | error | untested
    last_test_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<LLMProvider {self.name} ({self.provider}/{self.model_id})>"
