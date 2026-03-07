"""Gera guia de onboarding para devs novos a partir do codigo indexado."""

import hashlib
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

ONBOARDING_SYSTEM_PROMPT = (
    "Voce e um dev senior que acabou de entender completamente este sistema. "
    "Seu trabalho e criar um guia de onboarding para um dev novo que nunca viu este codigo. "
    "O guia deve indicar EXATAMENTE o que ler, em qual ordem e por que. "
    "Responda sempre em portugues brasileiro. "
    "Baseie-se APENAS no codigo fornecido. Seja especifico — cite arquivos e funcoes reais."
)

ONBOARDING_USER_TEMPLATE = """Crie um guia de onboarding completo para o repositorio "{repo_name}".

Estrutura obrigatoria:

# Guia de Onboarding — {repo_name}

## Visao geral em 5 minutos
{{explicacao do que o sistema faz em linguagem simples, sem jargao}}

## Antes de comecar
{{o que o dev novo precisa saber/instalar antes de qualquer coisa}}

## Ordem de leitura recomendada

### Passo 1 — Entenda a entrada do sistema
**Arquivo:** {{arquivo de entrada principal}}
**Por que ler primeiro:** {{motivo}}
**O que prestar atencao:** {{pontos especificos}}
**Tempo estimado:** {{X minutos}}

### Passo 2 — {{proximo arquivo/modulo critico}}
...

{{repete para 5 a 8 passos cobrindo os modulos mais importantes}}

## Mapa mental do sistema
{{descricao em texto de como os modulos se conectam — quem chama quem}}

## Armadilhas comuns
{{lista de coisas que costumam confundir devs novos neste sistema especifico}}

## Primeira tarefa sugerida
{{uma tarefa pequena e segura para o dev novo fazer para aprender fazendo}}

--- NOME DO REPOSITORIO ---
{repo_name}

--- ESTRUTURA DE ARQUIVOS ---
{file_structure}

--- PONTOS DE ENTRADA ---
{entry_points}

--- CODIGO DOS MODULOS PRINCIPAIS ---
{code_context}

--- CONTEXTO ADICIONAL (PRs, ADRs, decisoes) ---
{knowledge_context}"""


class OnboardingGenerator:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id

    def generate(self, repo_name: str, trigger: str = "manual") -> dict:
        """Gera guia de onboarding para um repositorio."""

        # Coleta contexto (reutiliza logica similar ao ReadmeGenerator)
        file_structure = self._get_file_structure(repo_name)
        entry_points = self._get_entry_points(repo_name)
        code_context = self._get_code_context(repo_name)
        knowledge_context = self._get_knowledge_context(repo_name)

        if not code_context:
            return {"error": "Nenhum codigo indexado para este repositorio"}

        user_message = ONBOARDING_USER_TEMPLATE.format(
            repo_name=repo_name,
            file_structure=file_structure[:3000],
            entry_points=entry_points[:4000],
            code_context=code_context[:12000],
            knowledge_context=knowledge_context[:4000],
        )

        try:
            result = llm_router.complete(
                db=self._db,
                system_prompt=ONBOARDING_SYSTEM_PROMPT,
                user_message=user_message,
                org_id=self._org_id,
                max_tokens=4096,
            )
            content = result["content"]
        except Exception as e:
            logger.error(f"Onboarding generation failed for {repo_name}: {e}")
            return {"error": str(e)}

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Conta passos no conteudo gerado
        steps_total = content.lower().count("### passo")
        if steps_total < 1:
            steps_total = 5  # fallback razoavel

        # Upsert em repo_docs
        existing = self._db.execute(text("""
            SELECT id FROM repo_docs
            WHERE org_id = :org_id AND repo_name = :repo_name AND doc_type = 'onboarding_guide'
            LIMIT 1
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().first()

        if existing:
            doc_id = existing["id"]
            self._db.execute(text("""
                UPDATE repo_docs
                SET content = :content, content_hash = :hash, generated_at = now(),
                    generation_trigger = :trigger, updated_at = now()
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
                VALUES (:id, :org_id, :repo_name, 'onboarding_guide', :content, :hash, :trigger)
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
            "doc_type": "onboarding_guide",
            "repo_name": repo_name,
            "content_hash": content_hash,
            "steps_total": steps_total,
        }

    def _get_file_structure(self, repo_name: str) -> str:
        rows = self._db.execute(text("""
            SELECT DISTINCT file_path
            FROM code_chunks
            WHERE org_id = :org_id AND repo_name = :repo_name
            ORDER BY file_path
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().all()
        if not rows:
            return "(Nenhum arquivo indexado)"
        return "\n".join([r["file_path"] for r in rows])

    def _get_entry_points(self, repo_name: str) -> str:
        from app.core.readme_generator import ENTRY_POINT_NAMES

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

    def _get_knowledge_context(self, repo_name: str) -> str:
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
