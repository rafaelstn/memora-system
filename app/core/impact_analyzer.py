"""Analisa o impacto de mudancas planejadas antes da implementacao."""
import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder
from app.integrations import llm_router

logger = logging.getLogger(__name__)

IDENTIFY_FILES_PROMPT = """Com base na descricao abaixo, identifique quais arquivos e funcoes
provavelmente serao modificados. Responda SOMENTE com JSON valido:
{{"files": ["caminho/arquivo.py"], "functions": ["nome_funcao"]}}

Descricao da mudanca: {description}"""

SYNTHESIS_PROMPT = """Voce e um arquiteto de software senior avaliando o risco de uma mudanca.

MUDANCA PROPOSTA:
{description}

DEPENDENCIAS IDENTIFICADAS:
{dependencies}

REGRAS DE NEGOCIO QUE PODEM SER AFETADAS:
{business_rules}

DECISOES ARQUITETURAIS RELACIONADAS:
{architecture_decisions}

MUDANCAS SIMILARES NO PASSADO:
{similar_changes}

Gere um relatorio de impacto em portugues com:
1. Nivel de risco geral: low | medium | high | critical
2. Resumo do risco em 2-3 frases
3. Lista de findings, cada um com:
   - type: dependency | business_rule | pattern_break | similar_change
   - severity: low | medium | high | critical
   - title: titulo curto
   - description: descricao do risco em portugues simples
   - affected_component: componente afetado (se aplicavel)
   - file_path: arquivo afetado (se aplicavel)
   - recommendation: como mitigar

Seja honesto sobre incertezas. Foque no que e realmente relevante.
Responda SOMENTE com JSON valido:
{{"risk_level": "...", "risk_summary": "...", "findings": [...]}}"""


class ImpactAnalyzer:
    def __init__(self, db: Session, org_id: str):
        self.db = db
        self.org_id = org_id

    def analyze(self, analysis_id: str):
        """Run full impact analysis pipeline."""
        analysis = self.db.execute(
            text("SELECT * FROM impact_analyses WHERE id = :id AND org_id = :org_id"),
            {"id": analysis_id, "org_id": self.org_id},
        ).mappings().first()

        if not analysis:
            logger.warning("Analise %s nao encontrada", analysis_id)
            return

        # Update status
        self.db.execute(
            text("UPDATE impact_analyses SET status = 'analyzing' WHERE id = :id"),
            {"id": analysis_id},
        )
        self.db.commit()

        try:
            description = analysis["change_description"]
            repo_name = analysis["repo_name"]
            affected_files = analysis.get("affected_files") or []

            # Step 1: Identify files if not provided
            if not affected_files:
                affected_files = self._identify_files(description)
                self.db.execute(
                    text("UPDATE impact_analyses SET affected_files = :files WHERE id = :id"),
                    {"files": json.dumps(affected_files), "id": analysis_id},
                )
                self.db.commit()

            # Step 2: Collect context (parallel queries)
            dependencies = self._find_dependencies(affected_files, repo_name)
            business_rules = self._find_related_rules(description)
            arch_decisions = self._find_arch_decisions(description)
            similar_changes = self._find_similar_changes(description)

            # Step 3: Synthesize with LLM
            result = self._synthesize(
                description, dependencies, business_rules, arch_decisions, similar_changes
            )

            # Step 4: Save findings
            risk_level = result.get("risk_level", "medium")
            if risk_level not in ("low", "medium", "high", "critical"):
                risk_level = "medium"

            for finding in result.get("findings", []):
                f_id = str(uuid.uuid4())
                f_type = finding.get("type", "dependency")
                if f_type not in ("dependency", "business_rule", "pattern_break", "similar_change"):
                    f_type = "dependency"
                f_severity = finding.get("severity", "medium")
                if f_severity not in ("low", "medium", "high", "critical"):
                    f_severity = "medium"

                self.db.execute(
                    text("""
                        INSERT INTO impact_findings
                            (id, analysis_id, org_id, finding_type, severity, title,
                             description, affected_component, file_path, recommendation)
                        VALUES (:id, :analysis_id, :org_id, :type, :severity, :title,
                                :description, :component, :file_path, :recommendation)
                    """),
                    {
                        "id": f_id,
                        "analysis_id": analysis_id,
                        "org_id": self.org_id,
                        "type": f_type,
                        "severity": f_severity,
                        "title": str(finding.get("title", ""))[:500],
                        "description": str(finding.get("description", ""))[:2000],
                        "component": str(finding.get("affected_component", ""))[:255] or None,
                        "file_path": str(finding.get("file_path", ""))[:500] or None,
                        "recommendation": str(finding.get("recommendation", "Verificar manualmente"))[:2000],
                    },
                )

            self.db.execute(
                text("""
                    UPDATE impact_analyses
                    SET risk_level = :risk, risk_summary = :summary, status = 'completed', updated_at = now()
                    WHERE id = :id
                """),
                {
                    "risk": risk_level,
                    "summary": str(result.get("risk_summary", ""))[:2000],
                    "id": analysis_id,
                },
            )
            self.db.commit()
            logger.info("Analise de impacto %s concluida: %s", analysis_id, risk_level)

        except Exception as e:
            logger.error("Falha na analise de impacto %s: %s", analysis_id, e)
            self.db.execute(
                text("UPDATE impact_analyses SET status = 'failed', updated_at = now() WHERE id = :id"),
                {"id": analysis_id},
            )
            self.db.commit()

    def _identify_files(self, description: str) -> list:
        """Use LLM to identify affected files from description."""
        try:
            result = llm_router.complete(
                db=self.db,
                system_prompt="Voce e um desenvolvedor identificando arquivos afetados por uma mudanca.",
                user_message=IDENTIFY_FILES_PROMPT.format(description=description),
                org_id=self.org_id,
                max_tokens=512,
            )
            parsed = json.loads(self._clean_json(result["content"]))
            return parsed.get("files", []) + parsed.get("functions", [])
        except Exception:
            return []

    def _find_dependencies(self, affected: list, repo_name: str) -> str:
        """Find code chunks that depend on the affected files/functions."""
        if not affected:
            return "Nenhuma dependencia identificada"

        parts = []
        for item in affected[:5]:
            rows = self.db.execute(
                text("""
                    SELECT file_path, chunk_name, chunk_type
                    FROM code_chunks
                    WHERE org_id = :org_id AND repo_name = :repo
                      AND content ILIKE :pattern
                    LIMIT 10
                """),
                {"org_id": self.org_id, "repo": repo_name, "pattern": f"%{item}%"},
            ).mappings().all()
            for r in rows:
                parts.append(f"- {r['file_path']}:{r['chunk_name']} ({r['chunk_type']}) usa '{item}'")

        return "\n".join(parts) or "Nenhuma dependencia direta encontrada"

    def _find_related_rules(self, description: str) -> str:
        """Find business rules related to the change via semantic search."""
        try:
            embedder = Embedder()
            embedding = embedder.embed_text(description)
            rows = self.db.execute(
                text("""
                    SELECT title, plain_english, rule_type,
                           1 - (embedding <=> CAST(:emb AS vector)) as score
                    FROM business_rules
                    WHERE org_id = :org_id
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT 5
                """),
                {"org_id": self.org_id, "emb": str(embedding)},
            ).mappings().all()
            parts = [
                f"- [{r['rule_type']}] {r['title']}: {r['plain_english']} (similaridade: {r['score']:.2f})"
                for r in rows if r["score"] > 0.5
            ]
            return "\n".join(parts) or "Nenhuma regra de negocio relacionada"
        except Exception:
            return "Nao foi possivel buscar regras de negocio"

    def _find_arch_decisions(self, description: str) -> str:
        """Find architecture decisions related to the change."""
        try:
            embedder = Embedder()
            embedding = embedder.embed_text(description)
            rows = self.db.execute(
                text("""
                    SELECT title, summary, source_type,
                           1 - (embedding <=> CAST(:emb AS vector)) as score
                    FROM knowledge_entries
                    WHERE org_id = :org_id AND source_type IN ('adr', 'pr', 'issue')
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT 5
                """),
                {"org_id": self.org_id, "emb": str(embedding)},
            ).mappings().all()
            parts = [
                f"- [{r['source_type']}] {r['title']}: {(r.get('summary') or '')[:200]}"
                for r in rows if r["score"] > 0.5
            ]
            return "\n".join(parts) or "Nenhuma decisao arquitetural relacionada"
        except Exception:
            return "Nao foi possivel buscar decisoes arquiteturais"

    def _find_similar_changes(self, description: str) -> str:
        """Find similar past changes from knowledge entries."""
        try:
            embedder = Embedder()
            embedding = embedder.embed_text(description)
            rows = self.db.execute(
                text("""
                    SELECT title, summary, source_type,
                           1 - (embedding <=> CAST(:emb AS vector)) as score
                    FROM knowledge_entries
                    WHERE org_id = :org_id AND source_type IN ('pr', 'commit')
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT 3
                """),
                {"org_id": self.org_id, "emb": str(embedding)},
            ).mappings().all()
            parts = [
                f"- {r['title']}: {(r.get('summary') or '')[:200]}"
                for r in rows if r["score"] > 0.5
            ]
            return "\n".join(parts) or "Nenhuma mudanca similar encontrada"
        except Exception:
            return "Nao foi possivel buscar mudancas similares"

    def _synthesize(self, description: str, deps: str, rules: str, decisions: str, similar: str) -> dict:
        """Use LLM to synthesize all context into a risk report."""
        prompt = SYNTHESIS_PROMPT.format(
            description=description,
            dependencies=deps,
            business_rules=rules,
            architecture_decisions=decisions,
            similar_changes=similar,
        )

        result = llm_router.complete(
            db=self.db,
            system_prompt="Voce e um arquiteto de software senior avaliando riscos.",
            user_message=prompt,
            org_id=self.org_id,
            max_tokens=4096,
        )

        return json.loads(self._clean_json(result["content"]))

    def _clean_json(self, raw: str) -> str:
        text_clean = raw.strip()
        if text_clean.startswith("```"):
            lines = text_clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text_clean = "\n".join(lines)
        return text_clean
