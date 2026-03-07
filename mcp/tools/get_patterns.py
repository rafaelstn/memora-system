"""Tool 3: Busca padroes e convencoes de codigo do time."""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder
from app.integrations import llm_router

logger = logging.getLogger(__name__)


def get_team_patterns(
    db: Session,
    org_id: str,
    context: str,
    language: str | None = None,
    repo_name: str | None = None,
) -> str:
    """Busca padroes e convencoes de codigo estabelecidos pelo time."""
    embedder = Embedder()
    embedding = embedder.embed_text(context)

    # 1. Busca ADRs de padroes
    adr_rows = db.execute(text("""
        SELECT title, summary
        FROM knowledge_entries
        WHERE org_id = :org_id AND source_type = 'adr'
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT 5
    """), {"org_id": org_id, "embedding": str(embedding)}).mappings().all()

    # 2. Busca codigo existente para identificar padroes
    code_conditions = ["org_id = :org_id"]
    code_params: dict = {"org_id": org_id, "embedding": str(embedding), "top_k": 10}

    if repo_name:
        code_conditions.append("repo_name = :repo_name")
        code_params["repo_name"] = repo_name

    code_where = " AND ".join(code_conditions)

    code_rows = db.execute(text(f"""
        SELECT file_path, chunk_name, chunk_type, content
        FROM code_chunks
        WHERE {code_where}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), code_params).mappings().all()

    if not adr_rows and not code_rows:
        return "Nenhum padrao de codigo identificado no sistema."

    # Monta contexto para analise
    adr_context = "\n".join(f"- {r['title']}: {r['summary']}" for r in adr_rows) if adr_rows else "Nenhum ADR encontrado."
    code_samples = "\n---\n".join(f"[{r['file_path']}:{r['chunk_name']}]\n{r['content'][:1000]}" for r in code_rows[:5])

    try:
        result = llm_router.complete(
            db=db,
            system_prompt="Voce analisa codigo e identifica padroes de desenvolvimento. Responda em portugues.",
            user_message=f"""Analise o codigo abaixo e identifique os padroes do time.
Contexto: {context}
{f'Linguagem: {language}' if language else ''}

ADRs e decisoes do time:
{adr_context}

Amostras de codigo:
{code_samples}

Liste os padroes identificados nos formatos:
- Naming: ...
- Estrutura: ...
- Tratamento de erros: ...
- Imports: ...
- Outros padroes relevantes: ...""",
            org_id=org_id,
            max_tokens=500,
        )
        return f"Padroes do time identificados:\n\n{result['content']}"
    except Exception as e:
        logger.error(f"Erro ao analisar padroes: {e}")
        # Fallback: retorna o que temos sem LLM
        parts = ["Padroes do time identificados (baseado em ADRs):\n"]
        for r in adr_rows:
            parts.append(f"- {r['title']}: {r['summary']}")
        return "\n".join(parts) if adr_rows else "Nao foi possivel identificar padroes."
