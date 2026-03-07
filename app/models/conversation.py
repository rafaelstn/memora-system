from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    sources = Column(JSONB)
    model_used = Column(String(100))
    tokens_used = Column(Integer)
    cost_usd = Column(Numeric(12, 8))
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


class Invite(Base):
    __tablename__ = "invites"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False)
    email = Column(String(255))
    created_by = Column(String(36), ForeignKey("users.id"))
    used_by = Column(String(36), ForeignKey("users.id"))
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
