"""
Teste live do Embedder contra a API da OpenAI.
Uso: python scripts/test_embedder_live.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.core.embedder import Embedder  # noqa: E402


def main():
    text = "Função que calcula o valor da fatura de água com base no consumo em m³"

    print(f"Texto: {text}")
    print()

    embedder = Embedder()

    print("Gerando embedding...")
    embedding = embedder.embed_text(text)

    print(f"Dimensões: {len(embedding)}")
    print(f"Primeiras 5 dimensões: {embedding[:5]}")
    assert len(embedding) == 1536, f"Esperado 1536, obtido {len(embedding)}"
    print("Vetor com 1536 dimensões: OK")

    print()
    cost = embedder.estimate_cost([text])
    print(f"Tokens estimados: {cost['tokens_estimados']}")
    print(f"Custo USD: ${cost['custo_usd']}")
    print(f"Custo BRL: R${cost['custo_brl']}")


if __name__ == "__main__":
    main()
