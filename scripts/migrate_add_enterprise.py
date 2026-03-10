"""Adiciona suporte ao modo Enterprise.

- ALTER organizations: ADD COLUMN mode VARCHAR DEFAULT 'saas'
- CREATE TABLE enterprise_db_configs (credenciais criptografadas do banco do cliente)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # 1. Adicionar coluna mode na organizations
        exists = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'organizations' AND column_name = 'mode'
        """)).first()

        if not exists:
            conn.execute(text("""
                ALTER TABLE organizations
                ADD COLUMN mode VARCHAR(20) NOT NULL DEFAULT 'saas'
            """))
            print("Coluna mode adicionada em organizations.")
        else:
            print("Coluna mode ja existe em organizations, pulando.")

        # 2. Criar tabela enterprise_db_configs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS enterprise_db_configs (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL UNIQUE REFERENCES organizations(id),
                host_encrypted TEXT NOT NULL,
                port INTEGER NOT NULL DEFAULT 5432,
                database_name_encrypted TEXT NOT NULL,
                username_encrypted TEXT NOT NULL,
                password_encrypted TEXT NOT NULL,
                ssl_mode VARCHAR(20) NOT NULL DEFAULT 'require',
                setup_complete BOOLEAN NOT NULL DEFAULT false,
                migration_log JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_enterprise_db_org ON enterprise_db_configs(org_id)"
        ))
        print("Tabela enterprise_db_configs criada.")

    print("\nMigracao enterprise concluida com sucesso.")


if __name__ == "__main__":
    migrate()
