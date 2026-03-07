import logging
import time

import tiktoken
from openai import OpenAI, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

PRICE_PER_1M_TOKENS = 0.02  # USD, text-embedding-3-small


class Embedder:
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY não configurada. Defina no .env.")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def _call_api(self, texts: list[str], max_retries: int = 3) -> list[list[float]]:
        for attempt in range(max_retries):
            try:
                response = self._client.embeddings.create(
                    model=settings.embedding_model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except RateLimitError:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt
                logger.warning(f"RateLimitError — retry {attempt + 1}/{max_retries} em {wait}s")
                time.sleep(wait)

    def embed_text(self, text: str) -> list[float]:
        tokens = self._encoder.encode(text)
        if len(tokens) > 8000:
            text = self._encoder.decode(tokens[:8000])
            logger.warning(f"Texto truncado de {len(tokens)} para 8000 tokens")
        return self._call_api([text])[0]

    def embed_batch(self, texts: list[str], on_batch_done=None) -> list[list[float]]:
        truncated = []
        for text in texts:
            if not text or not text.strip():
                truncated.append("# empty")
                continue
            tokens = self._encoder.encode(text)
            if len(tokens) > 8000:
                truncated.append(self._encoder.decode(tokens[:8000]))
            else:
                truncated.append(text)

        batch_size = settings.embedding_batch_size
        total_batches = (len(truncated) + batch_size - 1) // batch_size
        all_embeddings: list[list[float]] = []

        for i in range(0, len(truncated), batch_size):
            batch = truncated[i : i + batch_size]
            batch_num = i // batch_size + 1
            logger.info(f"Batch {batch_num}/{total_batches} processado")
            embeddings = self._call_api(batch)
            all_embeddings.extend(embeddings)

            if on_batch_done:
                on_batch_done(batch_num, total_batches)

            if batch_num < total_batches:
                time.sleep(0.5)

        return all_embeddings

    def estimate_cost(self, texts: list[str]) -> dict:
        total_tokens = sum(len(self._encoder.encode(t)) for t in texts)
        cost_usd = (total_tokens / 1_000_000) * PRICE_PER_1M_TOKENS
        cost_brl = cost_usd * settings.usd_to_brl

        return {
            "tokens_estimados": total_tokens,
            "custo_usd": round(cost_usd, 6),
            "custo_brl": round(cost_brl, 4),
        }


# Funções de conveniência usadas pelo ingestor
_embedder: Embedder | None = None


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    return _get_embedder()._call_api(texts)


def generate_embeddings_batched(texts: list[str], on_batch_done=None) -> list[list[float]]:
    return _get_embedder().embed_batch(texts, on_batch_done=on_batch_done)
