"""
Setup do banco de dados — cria extensão pgvector, tabela code_chunks e índice HNSW.
Uso: python scripts/setup_db.py
"""

import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import os

DATABASE_URL = os.getenv("DATABASE_URL")


def run():
    if not DATABASE_URL:
        print("DATABASE_URL não configurada no .env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("Criando extensão pgvector...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    print("Criando tabela code_chunks...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS code_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            repo_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(1024) NOT NULL,
            chunk_type VARCHAR(50) NOT NULL,
            chunk_name VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
    """)

    print("Criando índice HNSW no campo embedding...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_code_chunks_embedding
        ON code_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)

    print("Criando índice em repo_name...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_code_chunks_repo_name
        ON code_chunks (repo_name);
    """)

    cur.close()
    conn.close()
    print("Setup concluído com sucesso!")


if __name__ == "__main__":
    run()
