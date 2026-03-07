"""Revisao de codigo automatica — analisa bugs, seguranca, performance, consistencia e padroes."""

import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

# --- Prompts por categoria ---

SYSTEM_PROMPT = (
    "Voce e um revisor de codigo senior especializado em qualidade de software. "
    "Analise o codigo e responda SEMPRE em portugues brasileiro. "
    "Responda SOMENTE com o JSON solicitado, sem texto adicional."
)

BUGS_PROMPT = """Analise o codigo abaixo e identifique bugs e erros logicos.
Considere: condicoes de corrida, null pointer, edge cases nao tratados,
logica incorreta, loops infinitos, tratamento de erros ausente.
Para cada bug encontrado, explique o problema e sugira a correcao.
Responda em JSON: [{{"title": "...", "description": "...", "suggestion": "...", "file_path": "...", "line_start": null, "line_end": null, "code_snippet": "...", "severity": "critical|high|medium|low|info"}}]
Se nao encontrar problemas, retorne [].

{custom_instructions}

--- CODIGO ---
{code}"""

SECURITY_PROMPT = """Analise o codigo abaixo em busca de vulnerabilidades de seguranca.
Considere: SQL injection, XSS, CSRF, autenticacao fraca, dados sensiveis expostos,
dependencias vulneraveis, permissoes excessivas, validacao ausente de input.
Para cada vulnerabilidade, explique o risco e como mitigar.
Responda em JSON: [{{"title": "...", "description": "...", "suggestion": "...", "file_path": "...", "line_start": null, "line_end": null, "code_snippet": "...", "severity": "critical|high|medium|low|info"}}]
Se nao encontrar problemas, retorne [].

{custom_instructions}

--- CODIGO ---
{code}"""

PERFORMANCE_PROMPT = """Analise o codigo abaixo em busca de problemas de performance.
Considere: queries N+1, loops desnecessarios, operacoes sincronas que deveriam ser async,
estruturas de dados inadequadas, ausencia de cache, operacoes custosas em hot paths.
Responda em JSON: [{{"title": "...", "description": "...", "suggestion": "...", "file_path": "...", "line_start": null, "line_end": null, "code_snippet": "...", "severity": "critical|high|medium|low|info"}}]
Se nao encontrar problemas, retorne [].

{custom_instructions}

--- CODIGO ---
{code}"""

CONSISTENCY_PROMPT = """Analise se o codigo abaixo e consistente com o sistema existente.
Contexto do sistema atual:
{system_context}

Decisoes arquiteturais registradas:
{adrs_context}

Verifique: usa os mesmos padroes de acesso ao banco? Segue a estrutura de erros do sistema?
Reutiliza funcoes existentes ou duplica logica? Segue as convencoes de nomenclatura?
Responda em JSON: [{{"title": "...", "description": "...", "suggestion": "...", "file_path": "...", "line_start": null, "line_end": null, "code_snippet": "...", "severity": "critical|high|medium|low|info"}}]
Se nao encontrar problemas, retorne [].

{custom_instructions}

--- CODIGO ---
{code}"""

PATTERNS_PROMPT = """Analise se o codigo abaixo segue boas praticas e padroes do time.
Considere: naming conventions, tamanho de funcoes, complexidade ciclomatica,
comentarios e documentacao, separacao de responsabilidades, codigo duplicado.
Responda em JSON: [{{"title": "...", "description": "...", "suggestion": "...", "file_path": "...", "line_start": null, "line_end": null, "code_snippet": "...", "severity": "critical|high|medium|low|info"}}]
Se nao encontrar problemas, retorne [].

{custom_instructions}

--- CODIGO ---
{code}"""

SUMMARY_PROMPT = """Com base nos findings de revisao de codigo abaixo, gere um resumo executivo em portugues (2-3 paragrafos).
Destaque os problemas mais criticos, as areas que precisam de atencao, e elogios quando o codigo estiver bom.
Responda SOMENTE com o texto do resumo, sem formatacao JSON.

Score: {score}/100
Veredicto: {verdict}

Findings:
{findings_text}"""

# Category → prompt template
CATEGORY_PROMPTS = {
    "bug": BUGS_PROMPT,
    "security": SECURITY_PROMPT,
    "performance": PERFORMANCE_PROMPT,
    "consistency": CONSISTENCY_PROMPT,
    "pattern": PATTERNS_PROMPT,
}

# Severity score deductions
SEVERITY_DEDUCTIONS = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
    "info": 1,
}

VERDICT_LABELS = {
    "approved": "Aprovado",
    "approved_with_warnings": "Aprovado com ressalvas",
    "needs_changes": "Precisa de alteracoes",
    "rejected": "Rejeitado",
}


def _parse_findings_json(text_response: str) -> list[dict]:
    """Parse LLM response into list of findings, handling markdown fences."""
    content = text_response.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError:
        # Try to find JSON array in the response
        start = content.find("[")
        end = content.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass
        logger.warning(f"Could not parse findings JSON: {content[:200]}")
        return []


class CodeReviewer:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id

    def review(self, review_id: str) -> dict:
        """Run full review analysis on an existing code_review record."""
        # Mark as analyzing
        self._db.execute(
            text("UPDATE code_reviews SET status = 'analyzing', updated_at = now() WHERE id = :id"),
            {"id": review_id},
        )
        self._db.commit()

        # Load review
        review = self._db.execute(
            text("SELECT * FROM code_reviews WHERE id = :id"),
            {"id": review_id},
        ).mappings().first()

        if not review:
            raise ValueError(f"Review {review_id} nao encontrada")

        try:
            # Get code to review
            code = self._get_review_code(review)
            if not code:
                raise ValueError("Nenhum codigo para revisar")

            # Get system context for consistency analysis
            system_context = self._get_system_context(review)
            adrs_context = self._get_adrs_context()

            custom_instructions = review["custom_instructions"] or ""
            if custom_instructions:
                custom_instructions = f"\nInstrucoes adicionais do time:\n{custom_instructions}"

            # Run 5 category analyses in parallel
            all_findings = self._analyze_parallel(
                code, system_context, adrs_context, custom_instructions
            )

            # Calculate score and verdict
            score = self._calculate_score(all_findings)
            verdict = self._calculate_verdict(score, all_findings)

            # Generate summary
            summary = self._generate_summary(score, verdict, all_findings)

            # Save findings
            for finding in all_findings:
                finding_id = str(uuid.uuid4())
                self._db.execute(text("""
                    INSERT INTO review_findings
                        (id, review_id, org_id, category, severity, title, description,
                         suggestion, file_path, line_start, line_end, code_snippet)
                    VALUES (:id, :review_id, :org_id, :category, :severity, :title, :description,
                            :suggestion, :file_path, :line_start, :line_end, :code_snippet)
                """), {
                    "id": finding_id,
                    "review_id": review_id,
                    "org_id": self._org_id,
                    "category": finding["category"],
                    "severity": finding.get("severity", "info"),
                    "title": finding.get("title", "Finding"),
                    "description": finding.get("description", ""),
                    "suggestion": finding.get("suggestion"),
                    "file_path": finding.get("file_path"),
                    "line_start": finding.get("line_start"),
                    "line_end": finding.get("line_end"),
                    "code_snippet": finding.get("code_snippet"),
                })

            # Update review with results
            self._db.execute(text("""
                UPDATE code_reviews
                SET status = 'completed', overall_score = :score, overall_verdict = :verdict,
                    summary = :summary, updated_at = now()
                WHERE id = :id
            """), {
                "id": review_id,
                "score": score,
                "verdict": verdict,
                "summary": summary,
            })
            self._db.commit()

            return {
                "review_id": review_id,
                "status": "completed",
                "score": score,
                "verdict": verdict,
                "findings_count": len(all_findings),
            }

        except Exception as e:
            logger.error(f"Review failed for {review_id}: {e}")
            self._db.execute(text("""
                UPDATE code_reviews
                SET status = 'failed', summary = :error, updated_at = now()
                WHERE id = :id
            """), {"id": review_id, "error": f"Erro na analise: {e}"})
            self._db.commit()
            raise

    def _get_review_code(self, review: dict) -> str:
        """Get the code/diff to review."""
        if review["source_type"] == "manual":
            return review["code_snippet"] or ""

        # PR review — use stored diff or fetch from GitHub
        if review["diff"]:
            return review["diff"]

        # Fetch diff from GitHub API
        return self._fetch_pr_diff(review)

    def _fetch_pr_diff(self, review: dict) -> str:
        """Fetch PR diff from GitHub API."""
        repo_id = review["repo_id"]
        pr_number = review["pr_number"]
        if not repo_id or not pr_number:
            return ""

        # Get GitHub token
        gh = self._db.execute(
            text("SELECT github_token FROM github_integration WHERE org_id = :org_id AND is_active = true LIMIT 1"),
            {"org_id": self._org_id},
        ).mappings().first()

        if not gh:
            logger.warning("No GitHub token found for diff fetch")
            return ""

        token = gh["github_token"]
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.diff",
        }

        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo_id}/pulls/{pr_number}",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            diff = resp.text
            # Store for future reference
            self._db.execute(
                text("UPDATE code_reviews SET diff = :diff WHERE id = :id"),
                {"diff": diff[:100000], "id": review["id"]},
            )
            self._db.commit()
            return diff[:100000]
        except Exception as e:
            logger.error(f"Failed to fetch PR diff: {e}")
            return ""

    def _get_system_context(self, review: dict) -> str:
        """Get related code chunks for consistency analysis."""
        files_changed = review.get("files_changed") or []
        if not files_changed and review["source_type"] == "manual":
            return "(Sem contexto do sistema)"

        context_parts = []
        for file_path in files_changed[:5]:
            chunks = self._db.execute(text("""
                SELECT chunk_name, chunk_type, content
                FROM code_chunks
                WHERE org_id = :org_id AND file_path LIKE :pattern
                ORDER BY chunk_type
                LIMIT 5
            """), {
                "org_id": self._org_id,
                "pattern": f"%{file_path}%",
            }).mappings().all()

            for chunk in chunks:
                context_parts.append(
                    f"### {chunk['chunk_type']}: {chunk['chunk_name']}\n{chunk['content'][:1000]}"
                )

        return "\n".join(context_parts[:10]) if context_parts else "(Sem contexto do sistema)"

    def _get_adrs_context(self) -> str:
        """Get relevant ADRs for consistency analysis."""
        adrs = self._db.execute(text("""
            SELECT title, summary
            FROM knowledge_entries
            WHERE org_id = :org_id AND source_type = 'adr'
            ORDER BY created_at DESC
            LIMIT 5
        """), {"org_id": self._org_id}).mappings().all()

        if not adrs:
            return "(Sem ADRs registradas)"

        return "\n".join(
            f"- {adr['title']}: {(adr['summary'] or '')[:200]}"
            for adr in adrs
        )

    def _analyze_parallel(
        self, code: str, system_context: str, adrs_context: str, custom_instructions: str
    ) -> list[dict]:
        """Run all 5 category analyses in parallel."""
        # Truncate code for LLM context
        code_truncated = code[:15000]
        all_findings = []

        def analyze_category(category: str) -> list[dict]:
            template = CATEGORY_PROMPTS[category]
            if category == "consistency":
                user_msg = template.format(
                    code=code_truncated,
                    system_context=system_context[:5000],
                    adrs_context=adrs_context[:3000],
                    custom_instructions=custom_instructions,
                )
            else:
                user_msg = template.format(
                    code=code_truncated,
                    custom_instructions=custom_instructions,
                )

            try:
                result = llm_router.complete(
                    db=self._db,
                    system_prompt=SYSTEM_PROMPT,
                    user_message=user_msg,
                    org_id=self._org_id,
                    max_tokens=4096,
                )
                findings = _parse_findings_json(result["content"])
                # Tag each finding with category
                for f in findings:
                    f["category"] = category
                    # Validate severity
                    if f.get("severity") not in SEVERITY_DEDUCTIONS:
                        f["severity"] = "info"
                return findings
            except Exception as e:
                logger.error(f"Analysis failed for category {category}: {e}")
                return []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(analyze_category, cat): cat
                for cat in CATEGORY_PROMPTS
            }
            for future in as_completed(futures):
                category = futures[future]
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                    logger.info(f"Category {category}: {len(findings)} findings")
                except Exception as e:
                    logger.error(f"Category {category} failed: {e}")

        return all_findings

    def _calculate_score(self, findings: list[dict]) -> int:
        """Calculate overall score (0-100) based on findings."""
        score = 100
        for f in findings:
            severity = f.get("severity", "info")
            score -= SEVERITY_DEDUCTIONS.get(severity, 0)
        return max(0, score)

    def _calculate_verdict(self, score: int, findings: list[dict]) -> str:
        """Determine verdict based on score and findings."""
        severities = [f.get("severity") for f in findings]
        has_critical = "critical" in severities
        has_high = "high" in severities

        if score < 50 or has_critical:
            return "rejected"
        if score < 70 or has_high:
            return "needs_changes"
        if score < 85:
            return "approved_with_warnings"
        return "approved"

    def _generate_summary(self, score: int, verdict: str, findings: list[dict]) -> str:
        """Generate a natural language summary of the review."""
        if not findings:
            return "Codigo revisado sem problemas encontrados. O codigo segue boas praticas e esta pronto para merge."

        findings_text = ""
        for f in findings:
            findings_text += f"- [{f.get('severity', 'info').upper()}][{f.get('category', '?')}] {f.get('title', '?')}\n"

        try:
            user_msg = SUMMARY_PROMPT.format(
                score=score,
                verdict=VERDICT_LABELS.get(verdict, verdict),
                findings_text=findings_text[:4000],
            )
            result = llm_router.complete(
                db=self._db,
                system_prompt="Voce e um revisor de codigo senior. Escreva resumos claros em portugues brasileiro.",
                user_message=user_msg,
                org_id=self._org_id,
                max_tokens=1024,
            )
            return result["content"]
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return f"Revisao concluida com score {score}/100 ({VERDICT_LABELS.get(verdict, verdict)}). {len(findings)} problemas encontrados."


def fetch_pr_info(db: Session, org_id: str, repo_full_name: str, pr_number: int) -> dict | None:
    """Fetch PR metadata from GitHub API."""
    gh = db.execute(
        text("SELECT github_token FROM github_integration WHERE org_id = :org_id AND is_active = true LIMIT 1"),
        {"org_id": org_id},
    ).mappings().first()

    if not gh:
        return None

    token = gh["github_token"]
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        # Get PR info
        resp = requests.get(
            f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        pr = resp.json()

        # Get changed files
        files_resp = requests.get(
            f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/files",
            headers=headers,
            timeout=30,
        )
        files_resp.raise_for_status()
        files = [f["filename"] for f in files_resp.json()]

        return {
            "title": pr.get("title", ""),
            "author": pr.get("user", {}).get("login", ""),
            "url": pr.get("html_url", ""),
            "files_changed": files,
        }
    except Exception as e:
        logger.error(f"Failed to fetch PR info: {e}")
        return None
