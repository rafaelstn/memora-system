"""
Adiciona coluna password_hash à tabela users.
Uso: python scripts/migrate_add_password_hash.py
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

    cur.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
    """)

    print("Coluna password_hash adicionada com sucesso!")
    cur.close()
    conn.close()


if __name__ == "__main__":
    run()
