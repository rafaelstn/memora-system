"""
Migração: Cria tabelas do Módulo 3 — Memória Técnica.
Tabelas: knowledge_entries, knowledge_documents, knowledge_wikis
Uso: python scripts/migrate_add_knowledge.py
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def run():
    if not DATABASE_URL:
        print("DATABASE_URL nao configurada no .env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("Criando tabela knowledge_entries...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_entries (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            repo_id VARCHAR(36),
            source_type VARCHAR(20) NOT NULL,
            source_id VARCHAR(255),
            source_url VARCHAR(1024),
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            embedding vector(1536),
            file_paths JSONB,
            components JSONB,
            decision_type VARCHAR(50),
            extracted_at TIMESTAMP DEFAULT now(),
            source_date TIMESTAMP,
            created_by VARCHAR(36) REFERENCES users(id),
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_org ON knowledge_entries(org_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_repo ON knowledge_entries(repo_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source_type ON knowledge_entries(source_type);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_decision_type ON knowledge_entries(decision_type);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source_date ON knowledge_entries(source_date DESC);
    """)

    # HNSW index for vector search
    print("Criando indice HNSW para knowledge_entries...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_embedding
        ON knowledge_entries USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)

    print("Criando tabela knowledge_documents...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            repo_id VARCHAR(36),
            filename VARCHAR(500) NOT NULL,
            file_type VARCHAR(20) NOT NULL,
            file_size INTEGER NOT NULL,
            storage_path VARCHAR(1024) NOT NULL,
            processed BOOLEAN NOT NULL DEFAULT false,
            entry_id VARCHAR(36) REFERENCES knowledge_entries(id),
            uploaded_by VARCHAR(36) NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_documents_org ON knowledge_documents(org_id);
    """)

    print("Criando tabela knowledge_wikis...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_wikis (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            repo_id VARCHAR(36),
            component_name VARCHAR(255) NOT NULL,
            component_path VARCHAR(1024) NOT NULL,
            content TEXT NOT NULL,
            last_generated_at TIMESTAMP DEFAULT now(),
            generation_version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_wikis_org ON knowledge_wikis(org_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_wikis_repo ON knowledge_wikis(repo_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_wikis_component ON knowledge_wikis(component_path);
    """)

    cur.close()
    conn.close()
    print("Tabelas de conhecimento criadas com sucesso!")


if __name__ == "__main__":
    run()
