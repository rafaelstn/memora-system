"""
Cria todas as tabelas do Memora no Supabase.
Uso: python scripts/setup_tables.py
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

    print("Criando tabela organizations...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT now(),
            settings JSONB DEFAULT '{}'::jsonb
        );
        CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
    """)

    print("Criando tabela users...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'suporte',
            avatar_url VARCHAR(1024),
            is_active BOOLEAN NOT NULL DEFAULT true,
            invited_by VARCHAR(36),
            github_connected BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP,
            last_activity TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);
    """)

    print("Criando tabela conversations...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            repo_name VARCHAR(255) NOT NULL,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id),
            title VARCHAR(500) NOT NULL,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_conversations_repo ON conversations(repo_name);
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_org_id ON conversations(org_id);
    """)

    print("Criando tabela messages...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id VARCHAR(36) PRIMARY KEY,
            conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            sources JSONB,
            model_used VARCHAR(100),
            tokens_used INTEGER,
            cost_usd NUMERIC(12, 8),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
    """)

    print("Criando tabela invites...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            token VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(20) NOT NULL,
            email VARCHAR(255),
            created_by VARCHAR(36) REFERENCES users(id),
            used_by VARCHAR(36) REFERENCES users(id),
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT now(),
            expires_at TIMESTAMP NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_invites_token ON invites(token);
        CREATE INDEX IF NOT EXISTS idx_invites_org_id ON invites(org_id);
    """)

    print("Criando tabela github_integration...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS github_integration (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            installed_by VARCHAR(36) NOT NULL REFERENCES users(id),
            github_token TEXT NOT NULL,
            github_login VARCHAR(255) NOT NULL,
            github_avatar_url VARCHAR(1024),
            scopes TEXT,
            connected_at TIMESTAMP DEFAULT now(),
            last_used_at TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT true
        );
        CREATE INDEX IF NOT EXISTS idx_github_integration_active ON github_integration(is_active);
    """)

    # --- Monitor de Erros (Modulo 2) ---

    print("Criando tabela monitored_projects...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monitored_projects (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            description VARCHAR(500),
            token VARCHAR(255) UNIQUE NOT NULL,
            token_preview VARCHAR(8) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by VARCHAR(36) NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_monitored_projects_org ON monitored_projects(org_id);
        CREATE INDEX IF NOT EXISTS idx_monitored_projects_token ON monitored_projects(token);
    """)

    print("Criando tabela log_entries...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS log_entries (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL REFERENCES monitored_projects(id),
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            level VARCHAR(20) NOT NULL,
            message TEXT NOT NULL,
            source VARCHAR(500),
            stack_trace TEXT,
            metadata JSONB,
            received_at TIMESTAMP DEFAULT now(),
            occurred_at TIMESTAMP,
            is_analyzed BOOLEAN NOT NULL DEFAULT false,
            raw_payload JSONB
        );
        CREATE INDEX IF NOT EXISTS idx_log_entries_project ON log_entries(project_id);
        CREATE INDEX IF NOT EXISTS idx_log_entries_org ON log_entries(org_id);
        CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level);
        CREATE INDEX IF NOT EXISTS idx_log_entries_received ON log_entries(received_at DESC);
    """)

    print("Criando tabela error_alerts...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS error_alerts (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL REFERENCES monitored_projects(id),
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            log_entry_id VARCHAR(36) NOT NULL REFERENCES log_entries(id),
            title VARCHAR(500) NOT NULL,
            explanation TEXT NOT NULL,
            severity VARCHAR(20) NOT NULL,
            affected_component VARCHAR(255),
            suggested_actions JSONB,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            acknowledged_by VARCHAR(36) REFERENCES users(id),
            acknowledged_at TIMESTAMP,
            resolved_by VARCHAR(36) REFERENCES users(id),
            resolved_at TIMESTAMP,
            notification_sent BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_error_alerts_project ON error_alerts(project_id);
        CREATE INDEX IF NOT EXISTS idx_error_alerts_org ON error_alerts(org_id);
        CREATE INDEX IF NOT EXISTS idx_error_alerts_status ON error_alerts(status);
        CREATE INDEX IF NOT EXISTS idx_error_alerts_severity ON error_alerts(severity);
    """)

    print("Criando tabela alert_webhooks...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_webhooks (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            url TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by VARCHAR(36) NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_alert_webhooks_org ON alert_webhooks(org_id);
    """)

    # --- Memoria Tecnica (Modulo 3) ---

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
    print("Tabelas criadas com sucesso!")


if __name__ == "__main__":
    run()
