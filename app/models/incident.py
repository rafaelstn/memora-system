from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    alert_id = Column(String(36), ForeignKey("error_alerts.id"), nullable=True)
    project_id = Column(String(36), ForeignKey("monitored_projects.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False)  # low | medium | high | critical
    status = Column(String(20), nullable=False, default="open")  # open | investigating | mitigated | resolved
    declared_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    declared_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    mitigated_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_summary = Column(Text, nullable=True)
    postmortem = Column(Text, nullable=True)
    postmortem_generated_at = Column(DateTime, nullable=True)
    similar_incidents = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"

    id = Column(String(36), primary_key=True)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # declared | hypothesis | action | update | mitigated | resolved | comment
    content = Column(Text, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


class IncidentHypothesis(Base):
    __tablename__ = "incident_hypotheses"

    id = Column(String(36), primary_key=True)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    hypothesis = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.5)
    status = Column(String(20), nullable=False, default="open")  # open | confirmed | discarded
    confirmed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
