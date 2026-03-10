from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.chunk import Base


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    repo_id = Column(String(36), nullable=True)
    source_type = Column(String(20), nullable=False, index=True)  # pr | commit | issue | discussion | code | document | adr
    source_id = Column(String(255), nullable=True)
    source_url = Column(String(1024), nullable=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    file_paths = Column(JSONB, nullable=True)
    components = Column(JSONB, nullable=True)
    decision_type = Column(String(50), nullable=True, index=True)
    extracted_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    source_date = Column(DateTime, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgeEntry {self.source_type}:{self.title[:50]}>"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_id = Column(String(36), nullable=True)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(1024), nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    entry_id = Column(String(36), ForeignKey("knowledge_entries.id"), nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgeDocument {self.filename}>"


class KnowledgeWiki(Base):
    __tablename__ = "knowledge_wikis"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    repo_id = Column(String(36), nullable=True)
    component_name = Column(String(255), nullable=False)
    component_path = Column(String(1024), nullable=False, index=True)
    content = Column(Text, nullable=False)
    last_generated_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    generation_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgeWiki {self.component_name}>"
