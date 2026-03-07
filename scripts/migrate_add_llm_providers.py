"""Migration: create llm_providers table."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'llm_providers'
            )
        """))
        if result.scalar():
            print("Tabela llm_providers ja existe. Nada a fazer.")
            return

        conn.execute(text("""
            CREATE TABLE llm_providers (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                name VARCHAR(255) NOT NULL,
                provider VARCHAR(20) NOT NULL,
                model_id VARCHAR(255) NOT NULL,
                api_key_encrypted TEXT,
                base_url VARCHAR(1024),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                added_by VARCHAR(36) NOT NULL REFERENCES users(id),
                last_tested_at TIMESTAMP,
                last_test_status VARCHAR(20) NOT NULL DEFAULT 'untested',
                last_test_error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE INDEX idx_llm_providers_org_id ON llm_providers(org_id)
        """))

        conn.execute(text("""
            CREATE INDEX idx_llm_providers_active ON llm_providers(org_id, is_active)
        """))

        conn.commit()
        print("Tabela llm_providers criada com sucesso!")


if __name__ == "__main__":
    migrate()
