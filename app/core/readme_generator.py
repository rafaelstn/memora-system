"""Gera README.md automaticamente a partir do codigo indexado no repositorio."""

import hashlib
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

README_SYSTEM_PROMPT = (
    "Voce e um especialista em documentacao tecnica. "
    "Gere documentacao clara, completa e em portugues brasileiro. "
    "Baseie-se APENAS no codigo fornecido. Nao invente funcionalidades. "
    "Seja tecnico e preciso."
)

README_USER_TEMPLATE = """Analise o codigo abaixo e gere um README.md completo e profissional em portugues brasileiro.

Estrutura obrigatoria:

# {{Nome do Projeto}}
> {{tagline de uma linha descrevendo o que o sistema faz}}

## O que e
{{2-3 paragrafos explicando o proposito e o que o sistema faz}}

## Stack tecnologica
{{lista das principais tecnologias identificadas no codigo}}

## Estrutura do projeto
{{arvore de pastas principais com descricao de cada uma}}

## Como rodar localmente
{{passo a passo baseado nas configuracoes identificadas no codigo}}

## Variaveis de ambiente
{{tabela com todas as variaveis encontradas no codigo, descricao e se obrigatoria}}

## Principais modulos
{{para cada modulo principal: nome, responsabilidade, arquivos principais}}

## Fluxo principal
{{descreve o fluxo de dados/processamento principal do sistema}}

Baseie-se APENAS no codigo fornecido. Nao invente funcionalidades.

--- NOME DO REPOSITORIO ---
{repo_name}

--- ESTRUTURA DE ARQUIVOS ---
{file_structure}

--- PONTOS DE ENTRADA ---
{entry_points}

--- CODIGO DOS MODULOS PRINCIPAIS ---
{code_context}

--- VARIAVEIS DE AMBIENTE ENCONTRADAS ---
{env_vars}

--- CONTEXTO ADICIONAL (PRs, ADRs, decisoes) ---
{knowledge_context}"""


ENTRY_POINT_NAMES = {
    "main.py", "app.py", "index.js", "index.ts", "server.py", "server.js",
    "server.ts", "manage.py", "wsgi.py", "asgi.py", "__main__.py",
    "main.ts", "app.ts", "index.tsx", "app.tsx",
}


class ReadmeGenerator:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id

    def generate(self, repo_name: str, trigger: str = "manual") -> dict:
        """Gera README para um repositorio a partir dos chunks indexados."""

        # 1. Coleta contexto
        file_structure = self._get_file_structure(repo_name)
        entry_points = self._get_entry_points(repo_name)
        code_context = self._get_code_context(repo_name)
        env_vars = self._get_env_vars(repo_name)
        knowledge_context = self._get_knowledge_context(repo_name)

        if not code_context:
            return {"error": "Nenhum codigo indexado para este repositorio"}

        # 2. Gera com LLM
        user_message = README_USER_TEMPLATE.format(
            repo_name=repo_name,
            file_structure=file_structure[:3000],
            entry_points=entry_points[:4000],
            code_context=code_context[:12000],
            env_vars=env_vars[:2000],
            knowledge_context=knowledge_context[:4000],
        )

        try:
            result = llm_router.complete(
                db=self._db,
                system_prompt=README_SYSTEM_PROMPT,
                user_message=user_message,
                org_id=self._org_id,
                max_tokens=4096,
            )
            content = result["content"]
        except Exception as e:
            logger.error(f"README generation failed for {repo_name}: {e}")
            return {"error": str(e)}

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # 3. Upsert em repo_docs
        existing = self._db.execute(text("""
            SELECT id FROM repo_docs
            WHERE org_id = :org_id AND repo_name = :repo_name AND doc_type = 'readme'
            LIMIT 1
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().first()

        if existing:
            doc_id = existing["id"]
            self._db.execute(text("""
                UPDATE repo_docs
                SET content = :content, content_hash = :hash, generated_at = now(),
                    generation_trigger = :trigger, pushed_to_github = false, updated_at = now()
                WHERE id = :id
            """), {
                "content": content,
                "hash": content_hash,
                "trigger": trigger,
                "id": doc_id,
            })
        else:
            doc_id = str(uuid.uuid4())
            self._db.execute(text("""
                INSERT INTO repo_docs
                    (id, org_id, repo_name, doc_type, content, content_hash, generation_trigger)
                VALUES (:id, :org_id, :repo_name, 'readme', :content, :hash, :trigger)
            """), {
                "id": doc_id,
                "org_id": self._org_id,
                "repo_name": repo_name,
                "content": content,
                "hash": content_hash,
                "trigger": trigger,
            })

        self._db.commit()

        return {
            "doc_id": doc_id,
            "doc_type": "readme",
            "repo_name": repo_name,
            "content_hash": content_hash,
        }

    def _get_file_structure(self, repo_name: str) -> str:
        """Lista arquivos unicos do repo agrupados por pasta."""
        rows = self._db.execute(text("""
            SELECT DISTINCT file_path
            FROM code_chunks
            WHERE org_id = :org_id AND repo_name = :repo_name
            ORDER BY file_path
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().all()

        if not rows:
            return "(Nenhum arquivo indexado)"

        paths = [r["file_path"] for r in rows]
        return "\n".join(paths)

    def _get_entry_points(self, repo_name: str) -> str:
        """Busca conteudo dos arquivos de entrada."""
        rows = self._db.execute(text("""
            SELECT file_path, chunk_name, chunk_type, content
            FROM code_chunks
            WHERE org_id = :org_id AND repo_name = :repo_name
            ORDER BY file_path, chunk_name
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().all()

        entry_chunks = []
        for r in rows:
            filename = r["file_path"].split("/")[-1] if "/" in r["file_path"] else r["file_path"]
            if filename.lower() in ENTRY_POINT_NAMES:
                entry_chunks.append(f"### {r['file_path']} — {r['chunk_type']}: {r['chunk_name']}\n{r['content'][:2000]}")

        return "\n\n".join(entry_chunks) if entry_chunks else "(Nenhum ponto de entrada identificado)"

    def _get_code_context(self, repo_name: str) -> str:
        """Busca os chunks mais representativos do repo."""
        rows = self._db.execute(text("""
            SELECT file_path, chunk_name, chunk_type, content
            FROM code_chunks
            WHERE org_id = :org_id AND repo_name = :repo_name
            ORDER BY file_path, chunk_type, chunk_name
            LIMIT 50
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().all()

        if not rows:
            return ""

        parts = []
        for r in rows:
            parts.append(f"### {r['chunk_type']}: {r['chunk_name']} ({r['file_path']})\n{r['content'][:1000]}")
        return "\n\n".join(parts)

    def _get_env_vars(self, repo_name: str) -> str:
        """Identifica variaveis de ambiente no codigo."""
        rows = self._db.execute(text("""
            SELECT content
            FROM code_chunks
            WHERE org_id = :org_id AND repo_name = :repo_name
              AND (content LIKE '%os.environ%' OR content LIKE '%os.getenv%'
                   OR content LIKE '%process.env%' OR content LIKE '%environ.get%'
                   OR content LIKE '%Settings%' OR content LIKE '%BaseSettings%')
            LIMIT 20
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().all()

        if not rows:
            return "(Nenhuma variavel de ambiente encontrada)"

        env_content = "\n---\n".join([r["content"][:500] for r in rows])
        return env_content

    def _get_knowledge_context(self, repo_name: str) -> str:
        """Busca PRs, ADRs e decisoes do repo."""
        rows = self._db.execute(text("""
            SELECT title, summary, source_type, decision_type
            FROM knowledge_entries
            WHERE org_id = :org_id AND repo_id = :repo_name
            ORDER BY source_date DESC NULLS LAST
            LIMIT 10
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().all()

        if not rows:
            return "(Nenhum contexto adicional disponivel)"

        parts = []
        for r in rows:
            parts.append(f"- [{r['source_type']}] {r['title']}: {r['summary'][:200] if r['summary'] else '-'}")
        return "\n".join(parts)
