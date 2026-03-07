"""SQLAlchemy models for Security Analyzer."""
import uuid
from datetime import datetime, UTC

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.models.chunk import Base


class SecurityScan(Base):
    __tablename__ = "security_scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    repo_name = Column(String, nullable=False)
    requested_by = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending | analyzing | completed | failed
    security_score = Column(Integer, nullable=True)
    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    scanners_run = Column(JSONB, default=list)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC))


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("security_scans.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    scanner = Column(String, nullable=False)  # secrets | vulnerabilities | dependencies | config | patterns
    severity = Column(String, nullable=False)  # critical | high | medium | low | info
    category = Column(String, nullable=False)  # hardcoded_secret | sql_injection | xss | outdated_dep | ...
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    file_path = Column(String, nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    code_snippet = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    cwe_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class DependencyAlert(Base):
    __tablename__ = "dependency_alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("security_scans.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    package_name = Column(String, nullable=False)
    current_version = Column(String, nullable=True)
    ecosystem = Column(String, nullable=True)  # pypi | npm
    vulnerability_id = Column(String, nullable=True)  # OSV ID
    severity = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    fixed_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
