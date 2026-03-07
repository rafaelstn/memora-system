import logging
import time
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_api_key
from app.integrations.llm_clients import (
    AnthropicClient,
    GoogleClient,
    GroqClient,
    OllamaClient,
    OpenAIClient,
)

logger = logging.getLogger(__name__)


def _build_client(provider: str, api_key_encrypted: str | None, base_url: str | None):
    """Instantiate the correct LLM client based on provider type."""
    if provider == "ollama":
        return OllamaClient(base_url=base_url)

    if not api_key_encrypted:
        raise ValueError(f"API key obrigatoria para provedor {provider}")

    api_key = decrypt_api_key(api_key_encrypted)

    if provider == "openai":
        return OpenAIClient(api_key=api_key, base_url=base_url)
    elif provider == "anthropic":
        return AnthropicClient(api_key=api_key)
    elif provider == "google":
        return GoogleClient(api_key=api_key)
    elif provider == "groq":
        return GroqClient(api_key=api_key)
    else:
        raise ValueError(f"Provedor desconhecido: {provider}")


def _get_provider_row(db: Session, provider_id: str | None, org_id: str) -> dict:
    """Fetch provider config from DB. If provider_id is None, use the default."""
    if provider_id:
        row = db.execute(
            text("""
                SELECT id, name, provider, model_id, api_key_encrypted, base_url
                FROM llm_providers
                WHERE id = :id AND org_id = :org_id AND is_active = true
            """),
            {"id": provider_id, "org_id": org_id},
        ).mappings().first()
        if not row:
            raise ValueError(f"Provedor {provider_id} nao encontrado ou inativo")
        return dict(row)

    row = db.execute(
        text("""
            SELECT id, name, provider, model_id, api_key_encrypted, base_url
            FROM llm_providers
            WHERE org_id = :org_id AND is_default = true AND is_active = true
            LIMIT 1
        """),
        {"org_id": org_id},
    ).mappings().first()
    if not row:
        raise ValueError("Nenhum provedor LLM padrao configurado. Configure em Configuracoes > Modelos de IA.")
    return dict(row)


def complete(
    db: Session,
    system_prompt: str,
    user_message: str,
    org_id: str,
    provider_id: str | None = None,
    max_tokens: int = 2048,
) -> dict:
    """Non-streaming completion via the configured LLM provider."""
    start = time.time()
    prov = _get_provider_row(db, provider_id, org_id)
    client = _build_client(prov["provider"], prov["api_key_encrypted"], prov["base_url"])

    result = client.complete(system_prompt, user_message, prov["model_id"], max_tokens)
    latency_ms = int((time.time() - start) * 1000)

    return {
        "content": result["text"],
        "provider": prov["provider"],
        "provider_id": prov["id"],
        "provider_name": prov["name"],
        "model_id": prov["model_id"],
        "tokens_input": result["input_tokens"],
        "tokens_output": result["output_tokens"],
        "cost_usd": result["cost_usd"],
        "latency_ms": latency_ms,
    }


def stream(
    db: Session,
    system_prompt: str,
    user_message: str,
    org_id: str,
    provider_id: str | None = None,
    max_tokens: int = 2048,
) -> Iterator[tuple[str | None, dict | None]]:
    """Streaming completion — yields (text_chunk, meta) tuples.
    meta is None for text chunks, dict with tokens/cost for the final chunk."""
    prov = _get_provider_row(db, provider_id, org_id)
    client = _build_client(prov["provider"], prov["api_key_encrypted"], prov["base_url"])

    for text_chunk, meta in client.stream(system_prompt, user_message, prov["model_id"], max_tokens):
        if text_chunk:
            yield text_chunk, None
        if meta:
            yield None, {
                **meta,
                "provider": prov["provider"],
                "provider_id": prov["id"],
                "provider_name": prov["name"],
            }


def test_connection_raw(provider: str, model_id: str, api_key: str | None, base_url: str | None) -> dict:
    """Test LLM connection with raw credentials — no DB involved."""
    start = time.time()
    try:
        if provider == "ollama":
            client = OllamaClient(base_url=base_url)
        elif provider == "openai":
            client = OpenAIClient(api_key=api_key, base_url=base_url)
        elif provider == "anthropic":
            client = AnthropicClient(api_key=api_key)
        elif provider == "google":
            client = GoogleClient(api_key=api_key)
        elif provider == "groq":
            client = GroqClient(api_key=api_key)
        else:
            raise ValueError(f"Provedor desconhecido: {provider}")

        result = client.complete("Responda apenas: ok", "Teste de conexao", model_id, max_tokens=10)
        latency_ms = int((time.time() - start) * 1000)
        return {"status": "ok", "latency_ms": latency_ms, "response": result["text"][:50]}
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"status": "error", "latency_ms": latency_ms, "error": str(e)[:500]}


def test_provider(db: Session, provider_id: str, org_id: str) -> dict:
    """Test a provider with a simple prompt. Returns status + latency."""
    start = time.time()
    try:
        prov = _get_provider_row(db, provider_id, org_id)
        client = _build_client(prov["provider"], prov["api_key_encrypted"], prov["base_url"])
        result = client.complete("Responda apenas: ok", "Teste de conexao", prov["model_id"], max_tokens=10)
        latency_ms = int((time.time() - start) * 1000)

        # Update test status
        db.execute(
            text("""
                UPDATE llm_providers
                SET last_tested_at = NOW(), last_test_status = 'ok', last_test_error = NULL
                WHERE id = :id
            """),
            {"id": provider_id},
        )
        db.commit()

        return {"status": "ok", "latency_ms": latency_ms, "response": result["text"][:50]}
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        error_msg = str(e)[:500]

        db.execute(
            text("""
                UPDATE llm_providers
                SET last_tested_at = NOW(), last_test_status = 'error', last_test_error = :error
                WHERE id = :id
            """),
            {"id": provider_id, "error": error_msg},
        )
        db.commit()

        return {"status": "error", "latency_ms": latency_ms, "error": error_msg}
