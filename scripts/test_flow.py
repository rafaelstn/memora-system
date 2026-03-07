"""
Teste do fluxo completo: verifica banco, faz pergunta, mede tempo e custo.
Uso: python scripts/test_flow.py
"""

import os
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def check_db():
    print("1. Verificando banco de dados...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM code_chunks;")
    count = cur.fetchone()[0]
    print(f"   Chunks indexados: {count}")

    if count == 0:
        print("   AVISO: Nenhum chunk indexado. Execute index_repo.py primeiro.")
        cur.close()
        conn.close()
        return None

    cur.execute("SELECT DISTINCT repo_name FROM code_chunks;")
    repos = [r[0] for r in cur.fetchall()]
    print(f"   Repositórios: {', '.join(repos)}")

    cur.close()
    conn.close()
    return repos[0]


def test_ask(repo_name: str):
    import httpx

    print(f"\n2. Fazendo pergunta de teste para repo '{repo_name}'...")
    question = "Quais são as principais funções deste projeto e o que cada uma faz?"

    start = time.time()
    response = httpx.post(
        f"{API_BASE}/api/ask",
        json={"question": question, "repo_name": repo_name},
        timeout=60,
    )
    elapsed = time.time() - start

    data = response.json()

    print(f"\n3. Resposta ({elapsed:.1f}s):")
    print(f"   {data['answer'][:500]}...")

    print(f"\n4. Fontes ({len(data['sources'])}):")
    for s in data["sources"]:
        print(f"   - {s['file']} :: {s['chunk_name']}")

    print(f"\n5. Métricas:")
    print(f"   Tempo de resposta: {elapsed:.2f}s")
    print(f"   Fontes retornadas: {len(data['sources'])}")


def main():
    if not DATABASE_URL:
        print("DATABASE_URL não configurada no .env")
        sys.exit(1)

    repo_name = check_db()
    if repo_name:
        test_ask(repo_name)
    else:
        print("\nFluxo interrompido — indexe um repositório antes de testar.")


if __name__ == "__main__":
    main()
