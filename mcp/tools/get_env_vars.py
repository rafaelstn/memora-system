"""Tool 5: Lista variaveis de ambiente necessarias para o contexto."""

import logging
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ENV_PATTERN = re.compile(
    r'(?:os\.environ\.get|os\.getenv|os\.environ\[|settings\.)\s*[\(\["\']*(\w+)',
    re.IGNORECASE,
)


def get_environment_context(
    db: Session,
    org_id: str,
    context: str,
    repo_name: str | None = None,
) -> str:
    """Lista variaveis de ambiente e configuracoes relevantes para o contexto."""
    conditions = ["org_id = :org_id"]
    params: dict = {"org_id": org_id}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT file_path, content
        FROM code_chunks
        WHERE {where}
          AND (content LIKE '%os.environ%' OR content LIKE '%os.getenv%' OR content LIKE '%settings.%')
        LIMIT 50
    """), params).mappings().all()

    if not rows:
        return "Nenhuma variavel de ambiente identificada no codigo indexado."

    env_vars: dict[str, set[str]] = {}

    for r in rows:
        matches = ENV_PATTERN.findall(r["content"])
        for var_name in matches:
            # Filtra nomes curtos ou genericos demais
            if len(var_name) < 3 or var_name.lower() in ("self", "none", "true", "false"):
                continue
            if var_name not in env_vars:
                env_vars[var_name] = set()
            env_vars[var_name].add(r["file_path"])

    if not env_vars:
        return "Nenhuma variavel de ambiente identificada no codigo analisado."

    # Filtra por relevancia ao contexto (simples keyword match)
    context_lower = context.lower()
    relevant = {}
    other = {}

    for var, files in env_vars.items():
        if any(word in var.lower() for word in context_lower.split()):
            relevant[var] = files
        else:
            other[var] = files

    # Mostra relevantes primeiro, depois os demais
    all_vars = {**relevant, **other}

    parts = ["Variaveis de ambiente relevantes:\n"]
    for var_name, files in list(all_vars.items())[:20]:
        file_list = ", ".join(sorted(files)[:3])
        parts.append(f"{var_name}: (usada em {file_list})")

    return "\n".join(parts)
