"""Tool 4: Busca decisoes arquiteturais anteriores."""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder

logger = logging.getLogger(__name__)


def get_architecture_decisions(
    db: Session,
    org_id: str,
    context: str,
    repo_name: str | None = None,
) -> str:
    """Busca decisoes arquiteturais anteriores relacionadas ao contexto."""
    embedder = Embedder()
    embedding = embedder.embed_text(context)

    conditions = [
        "org_id = :org_id",
        "source_type IN ('adr', 'pr', 'issue')",
        "embedding IS NOT NULL",
    ]
    params: dict = {"org_id": org_id, "embedding": str(embedding), "top_k": 10}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT id, source_type, title, summary, source_url, created_at,
               ROUND((1 - (embedding <=> CAST(:embedding AS vector)))::numeric, 4) AS score
        FROM knowledge_entries
        WHERE {where}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), params).mappings().all()

    if not rows:
        return "Nenhuma decisao arquitetural relevante encontrada."

    parts = ["Decisoes anteriores relevantes:\n"]
    for r in rows:
        date = str(r["created_at"])[:10] if r["created_at"] else "?"
        source = r["source_url"] or "(sem link)"
        parts.append(
            f"[{date}] {r['title']}\n"
            f"{r['summary'][:500]}\n"
            f"Fonte: {source}\n"
        )

    return "\n".join(parts)


def get_architecture_decisions_raw(
    db: Session,
    org_id: str,
    context: str,
    repo_name: str | None = None,
) -> list[dict]:
    """Retorna decisoes estruturadas para uso pelo CodeGenerator."""
    embedder = Embedder()
    embedding = embedder.embed_text(context)

    conditions = [
        "org_id = :org_id",
        "source_type IN ('adr', 'pr', 'issue')",
        "embedding IS NOT NULL",
    ]
    params: dict = {"org_id": org_id, "embedding": str(embedding), "top_k": 10}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT id, source_type, title, summary, source_url, created_at
        FROM knowledge_entries
        WHERE {where}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), params).mappings().all()

    return [
        {
            "id": r["id"],
            "source_type": r["source_type"],
            "title": r["title"],
            "summary": r["summary"][:500] if r["summary"] else "",
            "source_url": r["source_url"],
        }
        for r in rows
    ]
