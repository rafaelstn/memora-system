from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class MonitoredProject(Base):
    __tablename__ = "monitored_projects"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    token = Column(String(255), unique=True, nullable=False, index=True)
    token_preview = Column(String(8), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("monitored_projects.id"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    level = Column(String(20), nullable=False)  # debug | info | warning | error | critical
    message = Column(Text, nullable=False)
    source = Column(String(500))
    stack_trace = Column(Text)
    metadata_ = Column("metadata", JSONB)
    received_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    occurred_at = Column(DateTime)
    is_analyzed = Column(Boolean, default=False, nullable=False)
    raw_payload = Column(JSONB)


class ErrorAlert(Base):
    __tablename__ = "error_alerts"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("monitored_projects.id"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    log_entry_id = Column(String(36), ForeignKey("log_entries.id"), nullable=False)
    title = Column(String(500), nullable=False)
    explanation = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # low | medium | high | critical
    affected_component = Column(String(255))
    suggested_actions = Column(JSONB)
    status = Column(String(20), nullable=False, default="open")  # open | acknowledged | resolved
    acknowledged_by = Column(String(36), ForeignKey("users.id"))
    acknowledged_at = Column(DateTime)
    resolved_by = Column(String(36), ForeignKey("users.id"))
    resolved_at = Column(DateTime)
    notification_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


class AlertWebhook(Base):
    __tablename__ = "alert_webhooks"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
