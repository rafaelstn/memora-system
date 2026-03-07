"""Tool 2: Busca regras de negocio relevantes."""

import json
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder

logger = logging.getLogger(__name__)


def get_business_rules(
    db: Session,
    org_id: str,
    context: str,
    rule_types: list[str] | None = None,
    repo_name: str | None = None,
) -> str:
    """Busca regras de negocio relevantes para o contexto de desenvolvimento."""
    embedder = Embedder()
    embedding = embedder.embed_text(context)

    conditions = ["org_id = :org_id", "is_active = true"]
    params: dict = {"org_id": org_id, "embedding": str(embedding), "top_k": 10}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name

    if rule_types:
        conditions.append("rule_type = ANY(:rule_types)")
        params["rule_types"] = rule_types

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT id, rule_type, title, plain_english, conditions, confidence,
               ROUND((1 - (embedding <=> CAST(:embedding AS vector)))::numeric, 4) AS score
        FROM business_rules
        WHERE {where}
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), params).mappings().all()

    if not rows:
        return "Nenhuma regra de negocio relevante encontrada."

    parts = ["Regras de negocio relevantes:\n"]
    for r in rows:
        conds = r["conditions"]
        if isinstance(conds, str):
            conds = json.loads(conds)
        cond_str = ""
        if conds:
            cond_items = []
            for c in conds:
                item = f"SE {c.get('if', '')}, ENTAO {c.get('then', '')}"
                if c.get("except"):
                    item += f", EXCETO {c['except']}"
                cond_items.append(item)
            cond_str = "\n  ".join(cond_items)

        parts.append(
            f"[{r['rule_type'].upper()}] {r['title']}\n"
            f"{r['plain_english']}\n"
            + (f"Condicoes:\n  {cond_str}\n" if cond_str else "")
        )

    return "\n".join(parts)


def get_business_rules_raw(
    db: Session,
    org_id: str,
    context: str,
    repo_name: str | None = None,
) -> list[dict]:
    """Retorna regras estruturadas para uso pelo CodeGenerator."""
    embedder = Embedder()
    embedding = embedder.embed_text(context)

    conditions = ["org_id = :org_id", "is_active = true"]
    params: dict = {"org_id": org_id, "embedding": str(embedding), "top_k": 10}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT id, rule_type, title, plain_english, conditions, confidence
        FROM business_rules
        WHERE {where}
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), params).mappings().all()

    return [
        {
            "id": r["id"],
            "rule_type": r["rule_type"],
            "title": r["title"],
            "plain_english": r["plain_english"],
            "conditions": r["conditions"] if isinstance(r["conditions"], list) else json.loads(r["conditions"] or "[]"),
        }
        for r in rows
    ]
