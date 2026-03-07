"""Gera wikis tecnicas por componente usando codigo + historico de decisoes."""

import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

WIKI_SYSTEM_PROMPT = (
    "Voce e um engenheiro de software senior especializado em documentacao tecnica. "
    "Gere wikis claras, completas e em portugues brasileiro."
)

WIKI_USER_TEMPLATE = """Gere uma wiki tecnica completa em portugues para o componente "{component_name}" ({component_path}).
Use as informacoes abaixo (codigo atual + historico de decisoes).
Estruture assim em Markdown:

## O que e
## Como funciona
## Decisoes de arquitetura
## Historico de mudancas relevantes
## Como modificar com seguranca
## Armadilhas conhecidas

--- CODIGO ATUAL ---
{code_context}

--- HISTORICO DE DECISOES ---
{knowledge_context}"""


class WikiGenerator:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id

    def generate(self, repo_id: str, component_path: str, component_name: str | None = None) -> dict:
        """Generate wiki for a component using code + knowledge history."""
        if not component_name:
            # Remove common extensions and format as title
            name = component_path.split("/")[-1]
            dot_pos = name.rfind(".")
            if dot_pos > 0:
                name = name[:dot_pos]
            component_name = name.replace("_", " ").replace("-", " ").title()

        # Fetch code chunks for this component
        code_chunks = self._db.execute(text("""
            SELECT chunk_name, chunk_type, content, file_path
            FROM code_chunks
            WHERE org_id = :org_id AND file_path LIKE :path_pattern
            ORDER BY chunk_type, chunk_name
            LIMIT 20
        """), {
            "org_id": self._org_id,
            "path_pattern": f"%{component_path}%",
        }).mappings().all()

        code_context = ""
        if code_chunks:
            for chunk in code_chunks:
                code_context += f"\n### {chunk['chunk_type']}: {chunk['chunk_name']} ({chunk['file_path']})\n"
                code_context += chunk["content"][:2000] + "\n"
        else:
            code_context = "(Nenhum codigo indexado para este componente)"

        # Fetch knowledge entries related to this component
        knowledge_entries = self._db.execute(text("""
            SELECT title, summary, source_type, decision_type, source_date
            FROM knowledge_entries
            WHERE org_id = :org_id
              AND (
                  file_paths::text LIKE :path_pattern
                  OR components::text LIKE :path_pattern
              )
            ORDER BY source_date DESC NULLS LAST
            LIMIT 10
        """), {
            "org_id": self._org_id,
            "path_pattern": f"%{component_path}%",
        }).mappings().all()

        knowledge_context = ""
        if knowledge_entries:
            for entry in knowledge_entries:
                date_str = str(entry["source_date"])[:10] if entry["source_date"] else "?"
                knowledge_context += f"\n- [{entry['source_type'].upper()}] {date_str} — {entry['title']}\n"
                if entry["summary"]:
                    knowledge_context += f"  {entry['summary'][:300]}\n"
        else:
            knowledge_context = "(Nenhum historico de decisoes encontrado)"

        # Generate wiki with LLM
        user_message = WIKI_USER_TEMPLATE.format(
            component_name=component_name,
            component_path=component_path,
            code_context=code_context[:8000],
            knowledge_context=knowledge_context[:4000],
        )

        try:
            result = llm_router.complete(
                db=self._db,
                system_prompt=WIKI_SYSTEM_PROMPT,
                user_message=user_message,
                org_id=self._org_id,
                max_tokens=4096,
            )
            wiki_content = result["content"]
        except Exception as e:
            logger.error(f"Wiki generation failed: {e}")
            wiki_content = f"# {component_name}\n\nErro ao gerar wiki: {e}"

        # Upsert wiki
        existing = self._db.execute(text("""
            SELECT id, generation_version FROM knowledge_wikis
            WHERE org_id = :org_id AND component_path = :path
            LIMIT 1
        """), {
            "org_id": self._org_id,
            "path": component_path,
        }).mappings().first()

        if existing:
            wiki_id = existing["id"]
            new_version = existing["generation_version"] + 1
            self._db.execute(text("""
                UPDATE knowledge_wikis
                SET content = :content, component_name = :name,
                    last_generated_at = now(), generation_version = :version,
                    updated_at = now(), repo_id = :repo_id
                WHERE id = :id
            """), {
                "content": wiki_content,
                "name": component_name,
                "version": new_version,
                "repo_id": repo_id,
                "id": wiki_id,
            })
        else:
            wiki_id = str(uuid.uuid4())
            new_version = 1
            self._db.execute(text("""
                INSERT INTO knowledge_wikis
                    (id, org_id, repo_id, component_name, component_path, content)
                VALUES (:id, :org_id, :repo_id, :name, :path, :content)
            """), {
                "id": wiki_id,
                "org_id": self._org_id,
                "repo_id": repo_id,
                "name": component_name,
                "path": component_path,
                "content": wiki_content,
            })

        self._db.commit()

        return {
            "wiki_id": wiki_id,
            "component_name": component_name,
            "component_path": component_path,
            "version": new_version,
        }
