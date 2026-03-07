"""Tool 1: Busca codigo similar no sistema Memora."""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder

logger = logging.getLogger(__name__)


def search_similar_code(
    db: Session,
    org_id: str,
    query: str,
    repo_name: str | None = None,
    top_k: int = 5,
) -> str:
    """Busca codigo similar existente no sistema para evitar duplicacao."""
    embedder = Embedder()
    embedding = embedder.embed_text(query)

    conditions = ["org_id = :org_id"]
    params: dict = {"org_id": org_id, "embedding": str(embedding), "top_k": top_k}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT repo_name, file_path, chunk_name, chunk_type, content,
               ROUND((1 - (embedding <=> CAST(:embedding AS vector)))::numeric, 4) AS score
        FROM code_chunks
        WHERE {where}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), params).mappings().all()

    if not rows:
        return "Nenhum codigo similar encontrado no sistema."

    parts = ["Codigo similar encontrado:\n"]
    for r in rows:
        score_pct = round(float(r["score"]) * 100, 1)
        parts.append(
            f"[{r['repo_name']} — {r['file_path']} — {r['chunk_name']}]\n"
            f"{r['content'][:2000]}\n"
            f"Similaridade: {score_pct}%\n"
        )

    return "\n".join(parts)


def search_similar_code_raw(
    db: Session,
    org_id: str,
    query: str,
    repo_name: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Retorna resultados estruturados para uso pelo CodeGenerator."""
    embedder = Embedder()
    embedding = embedder.embed_text(query)

    conditions = ["org_id = :org_id"]
    params: dict = {"org_id": org_id, "embedding": str(embedding), "top_k": top_k}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT repo_name, file_path, chunk_name, chunk_type, content,
               ROUND((1 - (embedding <=> CAST(:embedding AS vector)))::numeric, 4) AS score
        FROM code_chunks
        WHERE {where}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), params).mappings().all()

    return [
        {
            "repo_name": r["repo_name"],
            "file_path": r["file_path"],
            "chunk_name": r["chunk_name"],
            "content": r["content"][:2000],
            "score": float(r["score"]),
        }
        for r in rows
    ]
