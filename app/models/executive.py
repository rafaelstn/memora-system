from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class ExecutiveSnapshot(Base):
    __tablename__ = "executive_snapshots"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), nullable=False, index=True)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    health_score = Column(Integer, nullable=False, default=100)
    summary = Column(Text, nullable=True)
    highlights = Column(JSONB, nullable=True)
    risks = Column(JSONB, nullable=True)
    recommendations = Column(JSONB, nullable=True)
    metrics = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
