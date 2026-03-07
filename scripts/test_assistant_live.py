"""
Teste live do Assistant com 3 perguntas reais contra o Supabase + Claude.
Uso: python scripts/test_assistant_live.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.db.session import SessionLocal  # noqa: E402
from app.core.assistant import Assistant  # noqa: E402
from sqlalchemy import text  # noqa: E402


QUESTIONS = [
    "Quais funções existem no sistema?",
    "Como funciona o processo de geração de embeddings?",
    "Explica a arquitetura geral do projeto",
]


def get_repo_name(db):
    result = db.execute(text("SELECT DISTINCT repo_name FROM code_chunks LIMIT 1")).fetchone()
    if not result:
        print("Nenhum chunk indexado. Execute test_search_live.py primeiro.")
        sys.exit(1)
    return result[0]


def main():
    db = SessionLocal()
    total_cost = 0.0
    total_tokens = 0

    try:
        repo_name = get_repo_name(db)
        assistant = Assistant(db)
        print(f"Repo: {repo_name}")
        print("=" * 70)

        for i, question in enumerate(QUESTIONS, 1):
            print(f"\n{'='*70}")
            print(f"PERGUNTA {i}: {question}")
            print("=" * 70)

            result = assistant.ask(question, repo_name)

            print(f"\nRESPOSTA:\n{result['answer']}")

            print(f"\nFONTES ({len(result['sources'])}):")
            for s in result["sources"]:
                print(f"  - {s['file_path']} :: {s['chunk_name']} ({s['chunk_type']})")

            print(f"\nMÉTRICAS:")
            print(f"  Modelo: {result['model_used']}")
            print(f"  Tokens: {result['tokens_used']}")
            print(f"  Custo: ${result['cost_usd']:.6f}")
            print(f"  Latência: {result['latency_ms']}ms")

            total_cost += result["cost_usd"]
            total_tokens += result["tokens_used"]

        print(f"\n{'='*70}")
        print(f"TOTAL: {total_tokens} tokens | ${total_cost:.6f} USD")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
