"""
Migração: adapta tabelas para Supabase Auth + integração GitHub.

Mudanças:
- Remove github_id e password_hash de users
- Adiciona invited_by, github_connected, updated_at a users
- Cria tabela github_integration

Uso: python scripts/migrate_supabase_auth.py
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

    print("Migrando tabela users...")

    # Remove colunas antigas (ignora se nao existem)
    for col in ("github_id", "password_hash"):
        try:
            cur.execute(f"ALTER TABLE users DROP COLUMN IF EXISTS {col};")
            print(f"  Coluna {col} removida")
        except Exception as e:
            print(f"  Coluna {col}: {e}")

    # Adiciona colunas novas (ignora se ja existem)
    migrations = [
        ("invited_by", "VARCHAR(36)"),
        ("github_connected", "BOOLEAN NOT NULL DEFAULT false"),
        ("updated_at", "TIMESTAMP"),
    ]
    for col_name, col_type in migrations:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
            print(f"  Coluna {col_name} adicionada")
        except Exception as e:
            print(f"  Coluna {col_name}: {e}")

    print("Criando tabela github_integration...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS github_integration (
            id VARCHAR(36) PRIMARY KEY,
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

    cur.close()
    conn.close()
    print("Migração concluída!")


if __name__ == "__main__":
    run()
