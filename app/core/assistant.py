import logging
import re
import time

from sqlalchemy.orm import Session

from app.config import settings
from app.core.search import HybridSearch
from app.integrations.llm_client import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Você é um assistente técnico interno da empresa. "
    "Responda sempre em português brasileiro. Seja direto e técnico. "
    "Quando citar algo específico do código, mencione o arquivo de origem. "
    "Se a informação não estiver no contexto fornecido, diga explicitamente "
    "que não encontrou — nunca invente."
)

DEEP_REASONING_PATTERNS = re.compile(
    r"\b(explic|por\s+qu[eê]|como\s+funciona|analis|compar)\w*",
    re.IGNORECASE,
)


class Assistant:
    def __init__(self, db: Session):
        self._db = db
        self._search = HybridSearch(db)

    def _select_model(self, question: str) -> tuple[str, str]:
        provider = settings.llm_provider.lower()
        if DEEP_REASONING_PATTERNS.search(question):
            reason = "pergunta requer raciocínio profundo"
            if provider == "anthropic":
                return settings.claude_model_deep, reason
            return settings.openai_model_deep, reason
        reason = "consulta direta"
        if provider == "anthropic":
            return settings.claude_model_fast, reason
        return settings.openai_model_fast, reason

    def _build_user_message(self, question: str, chunks: list[dict]) -> str:
        parts = []
        for chunk in chunks:
            label_type = chunk["chunk_type"].capitalize()
            parts.append(
                f"[Arquivo: {chunk['file_path']} — {label_type}: {chunk['chunk_name']}]\n"
                f"{chunk['content']}\n"
                f"---"
            )

        context = "\n\n".join(parts)
        return f"{context}\n\nPergunta: {question}"

    def ask(self, question: str, repo_name: str, max_chunks: int = 5, org_id: str | None = None) -> dict:
        start = time.time()

        chunks = self._search.search(question, repo_name, top_k=max_chunks, org_id=org_id)

        if not chunks:
            return {
                "answer": (
                    "Não encontrei nenhum trecho de código indexado para esse repositório. "
                    "Verifique se a ingestão foi realizada."
                ),
                "sources": [],
                "model_used": None,
                "tokens_used": 0,
                "cost_usd": 0.0,
                "latency_ms": int((time.time() - start) * 1000),
            }

        sources = [
            {
                "file_path": c["file_path"],
                "chunk_name": c["chunk_name"],
                "chunk_type": c["chunk_type"],
                "preview": c["content"][:200],
            }
            for c in chunks
        ]

        # Modo search-only: sem nenhuma API key de LLM configurada
        provider = settings.llm_provider.lower()
        has_key = (
            (provider == "openai" and settings.openai_api_key)
            or (provider == "anthropic" and settings.anthropic_api_key)
        )
        if not has_key:
            latency_ms = int((time.time() - start) * 1000)
            summary = "\n".join(
                f"- **{c['chunk_type']}** `{c['chunk_name']}` em `{c['file_path']}`"
                for c in chunks
            )
            return {
                "answer": f"[Modo search-only — LLM não configurado]\n\nChunks encontrados:\n{summary}",
                "sources": sources,
                "model_used": "search-only",
                "tokens_used": 0,
                "cost_usd": 0.0,
                "latency_ms": latency_ms,
            }

        model, reason = self._select_model(question)
        logger.info(f"Modelo selecionado: {model} ({reason})")

        user_message = self._build_user_message(question, chunks)

        response = call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            model=model,
        )

        latency_ms = int((time.time() - start) * 1000)

        return {
            "answer": response["text"],
            "sources": sources,
            "model_used": response["model"],
            "tokens_used": response["total_tokens"],
            "cost_usd": response["cost_usd"],
            "latency_ms": latency_ms,
        }


# Função de conveniência para a rota /api/ask
def ask_assistant(
    db: Session,
    question: str,
    repo_name: str,
    max_chunks: int = 5,
    org_id: str | None = None,
) -> dict:
    assistant = Assistant(db)
    result = assistant.ask(question, repo_name, max_chunks, org_id=org_id)
    return {
        "answer": result["answer"],
        "sources": [
            {
                "file": s["file_path"],
                "chunk_name": s["chunk_name"],
                "content_preview": s["preview"],
            }
            for s in result["sources"]
        ],
    }
