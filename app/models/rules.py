from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class BusinessRule(Base):
    __tablename__ = "business_rules"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    rule_type = Column(String(20), nullable=False, index=True)  # calculation | validation | permission | integration | conditional
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    plain_english = Column(Text, nullable=False)
    conditions = Column(JSONB, nullable=True)
    affected_files = Column(JSONB, nullable=True)
    affected_functions = Column(JSONB, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    last_verified_at = Column(DateTime, nullable=True)
    changed_in_last_push = Column(Boolean, nullable=False, default=False)
    extracted_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<BusinessRule {self.rule_type}:{self.title[:50]}>"


class RuleChangeAlert(Base):
    __tablename__ = "rule_change_alerts"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey("business_rules.id"), nullable=False, index=True)
    change_type = Column(String(20), nullable=False)  # modified | removed | added
    previous_description = Column(Text, nullable=True)
    new_description = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    acknowledged_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<RuleChangeAlert {self.change_type}:{self.rule_id}>"


class RuleSimulation(Base):
    __tablename__ = "rule_simulations"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey("business_rules.id"), nullable=False, index=True)
    simulated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    input_values = Column(JSONB, nullable=False)
    result = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<RuleSimulation {self.rule_id}>"
