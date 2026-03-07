"""Security scanner — analisa codigo estaticamente para vulnerabilidades."""
import json
import logging
import re
import time
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

# ────────────── Patterns ──────────────

SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']([A-Za-z0-9_\-]{20,})["\']', "API Key exposta", "hardcoded_secret"),
    (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']', "Senha/Secret hardcoded", "hardcoded_secret"),
    (r'(?i)(token)\s*[=:]\s*["\']([A-Za-z0-9_\-\.]{20,})["\']', "Token hardcoded", "hardcoded_secret"),
    (r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[=:]\s*["\']([A-Za-z0-9/+=]{16,})["\']', "AWS Key exposta", "hardcoded_secret"),
    (r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----', "Chave privada no codigo", "hardcoded_secret"),
    (r'(?i)(DATABASE_URL|POSTGRES_PASSWORD|MONGO_URI)\s*[=:]\s*["\']([^"\']+)["\']', "Credencial de banco exposta", "hardcoded_secret"),
]

VULN_PATTERNS = [
    (r'(?i)execute\s*\(\s*["\'].*%s', "SQL Injection potencial (string formatting)", "sql_injection", "CWE-89"),
    (r'(?i)execute\s*\(\s*f["\']', "SQL Injection potencial (f-string)", "sql_injection", "CWE-89"),
    (r'(?i)\.execute\s*\(\s*["\'].*\+\s*\w+', "SQL Injection potencial (concatenacao)", "sql_injection", "CWE-89"),
    (r'(?i)eval\s*\(', "Uso de eval() — execucao de codigo arbitrario", "code_injection", "CWE-94"),
    (r'(?i)exec\s*\(', "Uso de exec() — execucao de codigo arbitrario", "code_injection", "CWE-94"),
    (r'(?i)subprocess\.\w+\(\s*["\'].*\+|subprocess\.call\(\s*[fF]', "Command injection potencial", "command_injection", "CWE-78"),
    (r'(?i)os\.system\s*\(', "Uso de os.system() — command injection", "command_injection", "CWE-78"),
    (r'(?i)(innerHTML|dangerouslySetInnerHTML|v-html)', "XSS potencial — HTML nao sanitizado", "xss", "CWE-79"),
    (r'(?i)pickle\.loads?\s*\(', "Deserializacao insegura (pickle)", "insecure_deserialization", "CWE-502"),
    (r'(?i)yaml\.load\s*\([^)]*\)(?!.*Loader)', "YAML load sem SafeLoader", "insecure_deserialization", "CWE-502"),
    (r'(?i)verify\s*=\s*False', "Verificacao SSL desabilitada", "ssl_bypass", "CWE-295"),
    (r'(?i)CORS\(.*allow_origins\s*=\s*\[\s*["\*"\']', "CORS aberto para todas origens", "cors_misconfiguration", "CWE-942"),
]

CONFIG_PATTERNS = [
    (r'(?i)DEBUG\s*=\s*True', "Debug habilitado", "debug_enabled"),
    (r'(?i)ALLOWED_HOSTS\s*=\s*\[\s*["\*"\']', "ALLOWED_HOSTS aberto", "permissive_config"),
    (r'(?i)SECRET_KEY\s*=\s*["\'](.{1,20})["\']', "SECRET_KEY fraca (curta demais)", "weak_secret"),
]

SEVERITY_MAP = {
    "hardcoded_secret": "critical",
    "sql_injection": "critical",
    "command_injection": "critical",
    "code_injection": "high",
    "xss": "high",
    "insecure_deserialization": "high",
    "ssl_bypass": "medium",
    "cors_misconfiguration": "medium",
    "debug_enabled": "medium",
    "permissive_config": "medium",
    "weak_secret": "high",
}


class SecurityScanner:
    def __init__(self, db: Session, org_id: str):
        self.db = db
        self.org_id = org_id

    def run(self, scan_id: str, repo_name: str):
        """Run all scanners for a repo."""
        start = time.time()
        findings = []
        scanners_run = []

        try:
            # Get code chunks for the repo
            chunks = self.db.execute(
                text("""
                    SELECT id, file_path, chunk_name, content, chunk_type
                    FROM code_chunks
                    WHERE org_id = :org_id AND repo_name = :repo_name
                """),
                {"org_id": self.org_id, "repo_name": repo_name},
            ).mappings().all()

            if not chunks:
                self._update_scan(scan_id, "completed", 100, [], [], 0)
                return

            # Scanner 1: Secrets Detection
            secret_findings = self._scan_secrets(chunks)
            findings.extend(secret_findings)
            scanners_run.append("secrets")

            # Scanner 2: Vulnerability Patterns
            vuln_findings = self._scan_vulnerabilities(chunks)
            findings.extend(vuln_findings)
            scanners_run.append("vulnerabilities")

            # Scanner 3: Config Audit
            config_findings = self._scan_config(chunks)
            findings.extend(config_findings)
            scanners_run.append("config")

            # Scanner 4: AI-powered pattern analysis
            ai_findings = self._scan_with_ai(chunks, repo_name)
            findings.extend(ai_findings)
            scanners_run.append("patterns")

            # Save findings
            for f in findings:
                finding_id = str(uuid.uuid4())
                self.db.execute(
                    text("""
                        INSERT INTO security_findings
                            (id, scan_id, org_id, scanner, severity, category,
                             title, description, file_path, line_start, line_end,
                             code_snippet, recommendation, cwe_id)
                        VALUES (:id, :scan_id, :org_id, :scanner, :severity, :category,
                                :title, :description, :file_path, :line_start, :line_end,
                                :code_snippet, :recommendation, :cwe_id)
                    """),
                    {
                        "id": finding_id,
                        "scan_id": scan_id,
                        "org_id": self.org_id,
                        **f,
                    },
                )

            # Calculate score
            score = self._calculate_score(findings)
            duration = int(time.time() - start)

            self._update_scan(scan_id, "completed", score, findings, scanners_run, duration)
            self.db.commit()

        except Exception as e:
            logger.error("Security scan failed: %s", e)
            self.db.execute(
                text("UPDATE security_scans SET status = 'failed', updated_at = now() WHERE id = :id"),
                {"id": scan_id},
            )
            self.db.commit()

    def _scan_secrets(self, chunks) -> list[dict]:
        findings = []
        for chunk in chunks:
            content = chunk["content"] or ""
            for pattern, title, category in SECRET_PATTERNS:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1
                    snippet = match.group(0)
                    # Mask the actual secret
                    if len(snippet) > 20:
                        snippet = snippet[:10] + "..." + snippet[-5:]
                    findings.append({
                        "scanner": "secrets",
                        "severity": "critical",
                        "category": category,
                        "title": title,
                        "description": f"Encontrado em {chunk['file_path']}:{line_num}. Credenciais nao devem estar no codigo.",
                        "file_path": chunk["file_path"],
                        "line_start": line_num,
                        "line_end": line_num,
                        "code_snippet": snippet,
                        "recommendation": "Mova para variavel de ambiente ou gerenciador de segredos (ex: AWS Secrets Manager, Vault).",
                        "cwe_id": "CWE-798",
                    })
        return findings

    def _scan_vulnerabilities(self, chunks) -> list[dict]:
        findings = []
        for chunk in chunks:
            content = chunk["content"] or ""
            for item in VULN_PATTERNS:
                pattern, title, category, cwe_id = item[0], item[1], item[2], item[3]
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append({
                        "scanner": "vulnerabilities",
                        "severity": SEVERITY_MAP.get(category, "medium"),
                        "category": category,
                        "title": title,
                        "description": f"Padrao de vulnerabilidade detectado em {chunk['file_path']}:{line_num}.",
                        "file_path": chunk["file_path"],
                        "line_start": line_num,
                        "line_end": line_num,
                        "code_snippet": match.group(0)[:200],
                        "recommendation": f"Revise e corrija o padrao ({cwe_id}).",
                        "cwe_id": cwe_id,
                    })
        return findings

    def _scan_config(self, chunks) -> list[dict]:
        findings = []
        for chunk in chunks:
            content = chunk["content"] or ""
            for pattern, title, category in CONFIG_PATTERNS:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append({
                        "scanner": "config",
                        "severity": SEVERITY_MAP.get(category, "medium"),
                        "category": category,
                        "title": title,
                        "description": f"Configuracao insegura em {chunk['file_path']}:{line_num}.",
                        "file_path": chunk["file_path"],
                        "line_start": line_num,
                        "line_end": line_num,
                        "code_snippet": match.group(0)[:200],
                        "recommendation": "Ajuste a configuracao para o ambiente de producao.",
                        "cwe_id": None,
                    })
        return findings

    def _scan_with_ai(self, chunks, repo_name: str) -> list[dict]:
        """Use LLM to detect complex patterns."""
        # Select a sample of chunks (limit to avoid token overflow)
        sample = chunks[:20]
        code_sample = "\n\n".join(
            f"# {c['file_path']}\n{(c['content'] or '')[:500]}" for c in sample
        )

        prompt = f"""Analise este codigo do repositorio '{repo_name}' e identifique problemas de seguranca
que nao seriam detectados por regex simples. Foque em:
- Logica de autenticacao/autorizacao falha
- Race conditions
- Vazamento de informacoes em respostas de erro
- Falta de validacao de entrada
- Padroes inseguros especificos do framework

Codigo:
{code_sample}

Responda em JSON valido (sem markdown):
[
  {{
    "severity": "critical|high|medium|low",
    "category": "auth_flaw|race_condition|info_leak|input_validation|framework_misuse",
    "title": "...",
    "description": "...",
    "file_path": "...",
    "recommendation": "..."
  }}
]
Se nenhum problema encontrado, retorne [].
"""
        try:
            result = llm_router.complete(
                db=self.db,
                system_prompt="Voce e um especialista em seguranca de aplicacoes.",
                user_message=prompt,
                org_id=self.org_id,
                max_tokens=2048,
            )
            raw = result["content"].strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines)
            items = json.loads(raw)
            findings = []
            for item in items[:10]:  # Limit to 10 findings from AI
                findings.append({
                    "scanner": "patterns",
                    "severity": item.get("severity", "medium"),
                    "category": item.get("category", "framework_misuse"),
                    "title": item.get("title", "Padrao inseguro detectado"),
                    "description": item.get("description", ""),
                    "file_path": item.get("file_path"),
                    "line_start": None,
                    "line_end": None,
                    "code_snippet": None,
                    "recommendation": item.get("recommendation", ""),
                    "cwe_id": None,
                })
            return findings
        except Exception as e:
            logger.warning("AI security scan failed: %s", e)
            return []

    def _calculate_score(self, findings: list[dict]) -> int:
        """Calculate security score 0-100."""
        score = 100
        for f in findings:
            sev = f.get("severity", "low")
            if sev == "critical":
                score -= 15
            elif sev == "high":
                score -= 8
            elif sev == "medium":
                score -= 3
            elif sev == "low":
                score -= 1
        return max(0, min(100, score))

    def _update_scan(self, scan_id: str, status: str, score: int,
                     findings: list[dict], scanners_run: list[str], duration: int):
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        high = sum(1 for f in findings if f.get("severity") == "high")
        medium = sum(1 for f in findings if f.get("severity") == "medium")
        low = sum(1 for f in findings if f.get("severity") in ("low", "info"))

        self.db.execute(
            text("""
                UPDATE security_scans SET
                    status = :status,
                    security_score = :score,
                    total_findings = :total,
                    critical_count = :critical,
                    high_count = :high,
                    medium_count = :medium,
                    low_count = :low,
                    scanners_run = :scanners,
                    duration_seconds = :duration,
                    updated_at = now()
                WHERE id = :id
            """),
            {
                "id": scan_id,
                "status": status,
                "score": score,
                "total": len(findings),
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
                "scanners": json.dumps(scanners_run),
                "duration": duration,
            },
        )
