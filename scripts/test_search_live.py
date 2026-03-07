"""
Teste live da busca híbrida contra o Supabase.
Se não houver chunks indexados, indexa o próprio Memora como teste.
Uso: python scripts/test_search_live.py
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.db.session import SessionLocal  # noqa: E402
from app.core.search import HybridSearch  # noqa: E402
from sqlalchemy import text  # noqa: E402


def ensure_indexed(db):
    """Verifica se há chunks. Se não, indexa o próprio Memora."""
    result = db.execute(text("SELECT COUNT(*) FROM code_chunks")).fetchone()
    count = result[0]

    if count > 0:
        repo = db.execute(
            text("SELECT DISTINCT repo_name FROM code_chunks LIMIT 1")
        ).fetchone()
        print(f"Chunks encontrados: {count} (repo: {repo[0]})")
        return repo[0]

    print("Nenhum chunk indexado. Indexando o próprio Memora...")
    from app.core.ingestor import ingest_repository
    repo_path = str(Path(__file__).resolve().parent.parent)
    result = ingest_repository(db=db, repo_path=repo_path, repo_name="memora")
    print(f"Indexação concluída: {result['files_processed']} arquivos, {result['chunks_created']} chunks")
    return "memora"


def main():
    db = SessionLocal()
    try:
        repo_name = ensure_indexed(db)
        searcher = HybridSearch(db)

        query = "como o sistema processa embeddings"
        print(f"\nQuery: \"{query}\"")
        print(f"Repo: {repo_name}")
        print("-" * 60)

        start = time.time()
        results = searcher.search(query, repo_name, top_k=5)
        elapsed_ms = (time.time() - start) * 1000

        for i, r in enumerate(results, 1):
            lines = r["content"].strip().splitlines()[:3]
            preview = "\n    ".join(lines)
            print(f"\n{i}. [{r['chunk_type']}] {r['chunk_name']}")
            print(f"   Arquivo: {r['file_path']}")
            print(f"   RRF Score: {r['rrf_score']}")
            print(f"   Preview:\n    {preview}")

        print(f"\nTempo total: {elapsed_ms:.0f}ms")
        print(f"Resultados: {len(results)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
