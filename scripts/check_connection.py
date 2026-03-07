"""
Verifica conexão com o banco e status da extensão pgvector.
Uso: python scripts/check_connection.py
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
        print("DATABASE_URL não configurada no .env")
        sys.exit(1)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"Conectado: {version}")

        cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        row = cur.fetchone()
        if row:
            print(f"pgvector: v{row[1]} (ativo)")
        else:
            print("pgvector: NÃO instalado")

        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'code_chunks';
        """)
        exists = cur.fetchone()[0] > 0
        print(f"Tabela code_chunks: {'existe' if exists else 'NÃO existe'}")

        if exists:
            cur.execute("SELECT COUNT(*) FROM code_chunks;")
            count = cur.fetchone()[0]
            print(f"Chunks indexados: {count}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao conectar: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
