"""Gerador de codigo com contexto real do sistema."""

import json
import logging

from sqlalchemy.orm import Session

from app.integrations import llm_router
from mcp.tools.search_code import search_similar_code_raw
from mcp.tools.get_rules import get_business_rules_raw
from mcp.tools.get_decisions import get_architecture_decisions_raw
from mcp.tools.get_env_vars import get_environment_context

logger = logging.getLogger(__name__)

CODEGEN_SYSTEM_PROMPT = (
    "Voce e um desenvolvedor senior especialista no sistema desta empresa. "
    "Gere codigo em portugues (comentarios) que seja consistente com o sistema existente. "
    "Siga EXATAMENTE os padroes identificados abaixo. "
    "Respeite TODAS as regras de negocio listadas. "
    "Reutilize codigo existente quando possivel — nao duplique logica."
)

CODEGEN_USER_TEMPLATE = """Solicitacao: {description}
Tipo: {request_type}
{file_context}
=== CODIGO SIMILAR EXISTENTE ===
{similar_code}

=== REGRAS DE NEGOCIO APLICAVEIS ===
{business_rules}

=== PADROES DO TIME ===
{team_patterns}

=== DECISOES ARQUITETURAIS RELEVANTES ===
{architecture_decisions}

=== VARIAVEIS DE AMBIENTE DISPONIVEIS ===
{env_vars}

Gere o codigo solicitado seguindo todo o contexto acima.
Apos o codigo, explique em portugues as principais decisoes tomadas."""


class CodeGenerator:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id

    def collect_context(
        self,
        description: str,
        repo_name: str,
        file_path: str | None = None,
    ) -> dict:
        """Coleta contexto do sistema para enriquecer a geracao."""
        context = {
            "similar_code": [],
            "business_rules": [],
            "team_patterns": "",
            "architecture_decisions": [],
            "env_vars": "",
            "file_context": "",
        }

        # Similar code
        try:
            context["similar_code"] = search_similar_code_raw(
                self._db, self._org_id, description, repo_name, top_k=5
            )
        except Exception as e:
            logger.warning(f"Erro ao buscar codigo similar: {e}")

        # Business rules
        try:
            context["business_rules"] = get_business_rules_raw(
                self._db, self._org_id, description, repo_name
            )
        except Exception as e:
            logger.warning(f"Erro ao buscar regras: {e}")

        # Team patterns (string)
        try:
            from mcp.tools.get_patterns import get_team_patterns
            context["team_patterns"] = get_team_patterns(
                self._db, self._org_id, description, repo_name=repo_name
            )
        except Exception as e:
            logger.warning(f"Erro ao buscar padroes: {e}")

        # Architecture decisions
        try:
            context["architecture_decisions"] = get_architecture_decisions_raw(
                self._db, self._org_id, description, repo_name
            )
        except Exception as e:
            logger.warning(f"Erro ao buscar decisoes: {e}")

        # Env vars (string)
        try:
            context["env_vars"] = get_environment_context(
                self._db, self._org_id, description, repo_name
            )
        except Exception as e:
            logger.warning(f"Erro ao buscar env vars: {e}")

        # File context
        if file_path:
            try:
                from sqlalchemy import text
                rows = self._db.execute(text("""
                    SELECT chunk_name, content FROM code_chunks
                    WHERE org_id = :org_id AND repo_name = :repo_name AND file_path = :file_path
                    ORDER BY chunk_name LIMIT 10
                """), {
                    "org_id": self._org_id,
                    "repo_name": repo_name,
                    "file_path": file_path,
                }).mappings().all()
                if rows:
                    context["file_context"] = "\n".join(f"[{r['chunk_name']}]\n{r['content'][:1500]}" for r in rows)
            except Exception as e:
                logger.warning(f"Erro ao buscar arquivo destino: {e}")

        return context

    def build_prompt(self, description: str, request_type: str, context: dict) -> str:
        """Monta o prompt enriquecido com contexto."""
        similar = "Nenhum codigo similar encontrado."
        if context.get("similar_code"):
            parts = []
            for c in context["similar_code"][:5]:
                parts.append(f"[{c['file_path']} — {c['chunk_name']}]\n{c['content']}")
            similar = "\n---\n".join(parts)

        rules = "Nenhuma regra de negocio aplicavel."
        if context.get("business_rules"):
            parts = []
            for r in context["business_rules"][:5]:
                parts.append(f"[{r['rule_type'].upper()}] {r['title']}\n{r['plain_english']}")
            rules = "\n\n".join(parts)

        decisions = "Nenhuma decisao anterior relevante."
        if context.get("architecture_decisions"):
            parts = []
            for d in context["architecture_decisions"][:5]:
                parts.append(f"[{d['source_type']}] {d['title']}\n{d['summary']}")
            decisions = "\n\n".join(parts)

        file_ctx = ""
        if context.get("file_context"):
            file_ctx = f"\nArquivo destino (codigo existente):\n{context['file_context']}\n"

        return CODEGEN_USER_TEMPLATE.format(
            description=description,
            request_type=request_type,
            file_context=file_ctx,
            similar_code=similar,
            business_rules=rules,
            team_patterns=context.get("team_patterns", "Nenhum padrao identificado."),
            architecture_decisions=decisions,
            env_vars=context.get("env_vars", "Nenhuma variavel identificada."),
        )

    def generate_stream(
        self,
        description: str,
        request_type: str,
        repo_name: str,
        file_path: str | None = None,
        use_context: bool = True,
    ):
        """Generator que coleta contexto e streama a resposta."""
        context = {}
        if use_context:
            context = self.collect_context(description, repo_name, file_path)

        prompt = self.build_prompt(description, request_type, context)

        # Yield context info
        yield {
            "type": "context",
            "data": {
                "similar_code_count": len(context.get("similar_code", [])),
                "rules_count": len(context.get("business_rules", [])),
                "has_patterns": bool(context.get("team_patterns")),
                "decisions_count": len(context.get("architecture_decisions", [])),
                "has_env_vars": bool(context.get("env_vars")),
            },
        }

        # Stream LLM response
        full_content = ""
        try:
            stream = llm_router.stream(
                db=self._db,
                system_prompt=CODEGEN_SYSTEM_PROMPT,
                user_message=prompt,
                org_id=self._org_id,
            )
            for chunk in stream:
                content = chunk.get("content", "")
                if content:
                    full_content += content
                    yield {"type": "token", "data": content}
        except Exception as e:
            logger.error(f"Erro ao gerar codigo: {e}")
            yield {"type": "error", "data": str(e)}
            return

        # Yield final result
        yield {
            "type": "done",
            "data": {
                "full_content": full_content,
                "context_used": {
                    "similar_code": context.get("similar_code", []),
                    "business_rules": context.get("business_rules", []),
                    "team_patterns": context.get("team_patterns", ""),
                    "architecture_decisions": context.get("architecture_decisions", []),
                    "env_vars": context.get("env_vars", ""),
                },
            },
        }
