from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    repo_name = Column(String(255), nullable=False)
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    change_description = Column(Text, nullable=False)
    affected_files = Column(JSONB, nullable=True)
    risk_level = Column(String(20), nullable=True)  # low | medium | high | critical
    risk_summary = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | analyzing | completed | failed
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


class ImpactFinding(Base):
    __tablename__ = "impact_findings"

    id = Column(String(36), primary_key=True)
    analysis_id = Column(String(36), ForeignKey("impact_analyses.id"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    finding_type = Column(String(30), nullable=False)  # dependency | business_rule | pattern_break | similar_change
    severity = Column(String(20), nullable=False)  # low | medium | high | critical
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    affected_component = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    related_rule_id = Column(String(36), nullable=True)
    related_entry_id = Column(String(36), nullable=True)
    recommendation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
