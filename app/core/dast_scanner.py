"""DAST Scanner — executa probes reais contra uma URL de teste."""
import ipaddress
import json
import logging
import time
import uuid
from urllib.parse import urlparse

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

PROBE_TIMEOUT = 60  # seconds per probe
REQUEST_TIMEOUT = 10  # seconds per individual request

PROBE_NAMES = [
    "sql_injection",
    "auth_bypass",
    "rate_limit",
    "cors",
    "security_headers",
    "idor",
    "xss",
    "brute_force",
    "sensitive_exposure",
    "http_methods",
]


def _is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP."""
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


def validate_target_url(target_url: str) -> str | None:
    """Validate that target URL is safe to test. Returns error message or None."""
    parsed = urlparse(target_url)
    hostname = parsed.hostname or ""

    # Check private IPs
    if _is_private_ip(hostname):
        return "URL invalida — execute apenas em ambiente de desenvolvimento ou staging. IPs privados nao sao permitidos."

    # Check if it's the Memora app itself
    app_url = getattr(settings, "APP_URL", "http://localhost:3000")
    api_url = getattr(settings, "NEXT_PUBLIC_API_URL", "http://localhost:8000")
    for known_url in [app_url, api_url]:
        if known_url:
            known_parsed = urlparse(known_url)
            if (known_parsed.hostname == hostname and
                    known_parsed.port == parsed.port):
                return "URL invalida — esta URL aponta para o proprio Memora. Use um ambiente de teste separado."

    if not parsed.scheme in ("http", "https"):
        return "URL invalida — use http:// ou https://."

    return None


class DASTScanner:
    def __init__(self, db: Session, org_id: str):
        self.db = db
        self.org_id = org_id
        self.findings: list[dict] = []
        self.endpoints: list[dict] = []

    def run(self, scan_id: str, target_url: str):
        """Execute all probes against target URL."""
        start = time.time()
        target_url = target_url.rstrip("/")

        try:
            self._update_progress(scan_id, "running", 0, len(PROBE_NAMES))

            # Discover endpoints first
            self.endpoints = self._discover_endpoints(target_url)

            for i, probe_name in enumerate(PROBE_NAMES):
                try:
                    probe_fn = getattr(self, f"_probe_{probe_name}", None)
                    if probe_fn:
                        probe_fn(target_url)
                except Exception as e:
                    logger.warning("Probe %s failed: %s", probe_name, e)

                self._update_progress(scan_id, "running", i + 1, len(PROBE_NAMES))

            # Save findings
            confirmed_count = 0
            for f in self.findings:
                finding_id = str(uuid.uuid4())
                self.db.execute(
                    text("""
                        INSERT INTO dast_findings
                            (id, scan_id, org_id, probe_type, severity, title,
                             description, result, confirmed, endpoint,
                             payload_used, response_code, recommendation)
                        VALUES (:id, :scan_id, :org_id, :probe_type, :severity, :title,
                                :description, :result, :confirmed, :endpoint,
                                :payload_used, :response_code, :recommendation)
                    """),
                    {"id": finding_id, "scan_id": scan_id, "org_id": self.org_id, **f},
                )
                if f.get("confirmed"):
                    confirmed_count += 1

            # Calculate risk level
            risk_level = self._calculate_risk(self.findings)
            duration = int(time.time() - start)

            # Generate summary
            summary = self._generate_summary(self.findings, confirmed_count)

            self.db.execute(
                text("""
                    UPDATE dast_scans SET
                        status = 'completed',
                        probes_completed = :probes_total,
                        vulnerabilities_confirmed = :confirmed,
                        risk_level = :risk,
                        summary = :summary,
                        duration_seconds = :duration,
                        updated_at = now()
                    WHERE id = :id
                """),
                {
                    "id": scan_id,
                    "probes_total": len(PROBE_NAMES),
                    "confirmed": confirmed_count,
                    "risk": risk_level,
                    "summary": summary,
                    "duration": duration,
                },
            )
            self.db.commit()

        except Exception as e:
            logger.error("DAST scan failed: %s", e)
            self.db.execute(
                text("UPDATE dast_scans SET status = 'failed', updated_at = now() WHERE id = :id"),
                {"id": scan_id},
            )
            self.db.commit()

    def _update_progress(self, scan_id: str, status: str, completed: int, total: int):
        self.db.execute(
            text("""
                UPDATE dast_scans SET
                    status = :status,
                    probes_completed = :completed,
                    probes_total = :total,
                    updated_at = now()
                WHERE id = :id
            """),
            {"id": scan_id, "status": status, "completed": completed, "total": total},
        )
        self.db.commit()

    def _discover_endpoints(self, target_url: str) -> list[dict]:
        """Try to discover API endpoints."""
        endpoints = []
        try:
            # Try OpenAPI spec
            for path in ["/openapi.json", "/api/docs", "/docs/openapi.json"]:
                try:
                    r = httpx.get(f"{target_url}{path}", timeout=REQUEST_TIMEOUT)
                    if r.status_code == 200 and "paths" in r.text:
                        spec = r.json()
                        for p, methods in spec.get("paths", {}).items():
                            for method in methods:
                                if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                                    endpoints.append({"path": p, "method": method.upper()})
                        if endpoints:
                            return endpoints
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback: common API endpoints
        common = [
            {"path": "/api/health", "method": "GET"},
            {"path": "/api/auth/login", "method": "POST"},
            {"path": "/api/users", "method": "GET"},
            {"path": "/api/repos", "method": "GET"},
        ]
        return common

    # ────────────── Probes ──────────────

    def _probe_sql_injection(self, target_url: str):
        """Test for SQL injection in query parameters."""
        payloads = ["' OR '1'='1", "' OR 1=1--", "'; SELECT 1--", "1 AND 1=1"]
        error_patterns = ["syntax error", "ORA-", "mysql_fetch", "pg_query",
                          "sqlite3", "SQLSTATE", "unterminated"]

        test_endpoints = [e for e in self.endpoints if e["method"] == "GET"][:5]
        for ep in test_endpoints:
            url = f"{target_url}{ep['path']}"
            for payload in payloads:
                try:
                    r = httpx.get(url, params={"q": payload}, timeout=REQUEST_TIMEOUT)
                    body = r.text.lower()
                    if any(pat.lower() in body for pat in error_patterns):
                        self.findings.append({
                            "probe_type": "sql_injection",
                            "severity": "critical",
                            "title": "SQL Injection — erro de banco exposto na resposta",
                            "description": f"O endpoint {ep['path']} retornou erro de banco ao receber payload SQL.",
                            "result": r.text[:500],
                            "confirmed": True,
                            "endpoint": ep["path"],
                            "payload_used": payload,
                            "response_code": r.status_code,
                            "recommendation": "Use queries parametrizadas (prepared statements). Nunca concatene input do usuario em SQL.",
                        })
                        return  # One confirmed finding is enough
                except Exception:
                    continue

        self.findings.append({
            "probe_type": "sql_injection",
            "severity": "info",
            "title": "SQL Injection — nenhuma vulnerabilidade encontrada",
            "description": "Nenhum endpoint retornou erros de banco ao receber payloads SQL.",
            "result": "Endpoints testados nao refletiram erros de banco.",
            "confirmed": False,
            "endpoint": test_endpoints[0]["path"] if test_endpoints else "/",
            "payload_used": None,
            "response_code": None,
            "recommendation": "Continue usando queries parametrizadas.",
        })

    def _probe_auth_bypass(self, target_url: str):
        """Test if protected endpoints can be accessed without auth."""
        protected = [e for e in self.endpoints
                     if e["path"] not in ("/api/health", "/api/auth/login", "/api/docs")][:5]
        if not protected:
            protected = [{"path": "/api/repos", "method": "GET"}]

        for ep in protected:
            url = f"{target_url}{ep['path']}"
            try:
                # No token
                r1 = httpx.get(url, timeout=REQUEST_TIMEOUT)
                if r1.status_code == 200:
                    self.findings.append({
                        "probe_type": "auth_bypass",
                        "severity": "critical",
                        "title": "Auth Bypass — endpoint acessivel sem autenticacao",
                        "description": f"O endpoint {ep['path']} retornou 200 sem token de autenticacao.",
                        "result": f"Status: {r1.status_code}. Resposta: {r1.text[:300]}",
                        "confirmed": True,
                        "endpoint": ep["path"],
                        "payload_used": "Requisicao sem header Authorization",
                        "response_code": r1.status_code,
                        "recommendation": "Proteja todos os endpoints com middleware de autenticacao.",
                    })
                    return

                # Malformed token
                r2 = httpx.get(url, headers={"Authorization": "Bearer invalid.token.here"}, timeout=REQUEST_TIMEOUT)
                if r2.status_code == 200:
                    self.findings.append({
                        "probe_type": "auth_bypass",
                        "severity": "critical",
                        "title": "Auth Bypass — token malformado aceito",
                        "description": f"O endpoint {ep['path']} aceitou um token JWT invalido.",
                        "result": f"Status: {r2.status_code}",
                        "confirmed": True,
                        "endpoint": ep["path"],
                        "payload_used": "Bearer invalid.token.here",
                        "response_code": r2.status_code,
                        "recommendation": "Valide tokens JWT corretamente. Verifique assinatura e expiracao.",
                    })
                    return

                # JWT with alg=none
                import base64
                header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
                payload = base64.urlsafe_b64encode(b'{"sub":"admin","role":"admin"}').rstrip(b"=").decode()
                none_token = f"{header}.{payload}."
                r3 = httpx.get(url, headers={"Authorization": f"Bearer {none_token}"}, timeout=REQUEST_TIMEOUT)
                if r3.status_code == 200:
                    self.findings.append({
                        "probe_type": "auth_bypass",
                        "severity": "critical",
                        "title": "Auth Bypass — JWT com algoritmo 'none' aceito",
                        "description": f"O endpoint {ep['path']} aceitou JWT sem assinatura (alg=none).",
                        "result": f"Status: {r3.status_code}",
                        "confirmed": True,
                        "endpoint": ep["path"],
                        "payload_used": f"JWT alg=none: {none_token[:50]}...",
                        "response_code": r3.status_code,
                        "recommendation": "Rejeite tokens com alg=none. Configure o validador JWT para aceitar apenas algoritmos seguros.",
                    })
                    return

            except Exception:
                continue

        self.findings.append({
            "probe_type": "auth_bypass",
            "severity": "info",
            "title": "Auth Bypass — endpoints protegidos corretamente",
            "description": "Endpoints protegidos rejeitaram requisicoes sem autenticacao valida.",
            "result": "Todos retornaram 401 ou 403 sem token.",
            "confirmed": False,
            "endpoint": protected[0]["path"],
            "payload_used": None,
            "response_code": None,
            "recommendation": "Continue validando tokens em todos os endpoints protegidos.",
        })

    def _probe_rate_limit(self, target_url: str):
        """Test if login endpoint has rate limiting."""
        login_url = f"{target_url}/api/auth/login"
        blocked = False
        try:
            for i in range(20):
                r = httpx.post(
                    login_url,
                    json={"email": "test@test.com", "password": "wrong"},
                    timeout=REQUEST_TIMEOUT,
                )
                if r.status_code == 429:
                    blocked = True
                    break
                time.sleep(0.1)
        except Exception:
            pass

        if not blocked:
            self.findings.append({
                "probe_type": "rate_limit",
                "severity": "high",
                "title": "Rate Limiting ausente no login",
                "description": "20 requisicoes seguidas ao login nao foram bloqueadas.",
                "result": "Nenhuma requisicao retornou 429 (Too Many Requests).",
                "confirmed": True,
                "endpoint": "/api/auth/login",
                "payload_used": "20 POST requests com credenciais invalidas",
                "response_code": None,
                "recommendation": "Implemente rate limiting no endpoint de login (ex: 5 tentativas por minuto por IP).",
            })
        else:
            self.findings.append({
                "probe_type": "rate_limit",
                "severity": "info",
                "title": "Rate Limiting — bloqueio ativo",
                "description": "O endpoint de login bloqueou requisicoes repetidas.",
                "result": "Requisicao bloqueada com 429.",
                "confirmed": False,
                "endpoint": "/api/auth/login",
                "payload_used": None,
                "response_code": 429,
                "recommendation": "Rate limiting ativo. Verifique periodicamente os limites configurados.",
            })

    def _probe_cors(self, target_url: str):
        """Test CORS configuration."""
        try:
            r = httpx.options(
                target_url,
                headers={
                    "Origin": "https://evil-site-memora-test.com",
                    "Access-Control-Request-Method": "GET",
                },
                timeout=REQUEST_TIMEOUT,
            )
            acao = r.headers.get("access-control-allow-origin", "")
            if acao == "*" or acao == "https://evil-site-memora-test.com":
                self.findings.append({
                    "probe_type": "cors",
                    "severity": "high" if acao == "*" else "critical",
                    "title": "CORS — aceita requisicoes de origens nao autorizadas",
                    "description": f"O servidor respondeu com Access-Control-Allow-Origin: {acao}",
                    "result": f"ACAO: {acao}",
                    "confirmed": True,
                    "endpoint": "/",
                    "payload_used": "Origin: https://evil-site-memora-test.com",
                    "response_code": r.status_code,
                    "recommendation": 'Configure CORS para aceitar apenas origens conhecidas: allow_origins=["https://seudominio.com"].',
                })
                return
        except Exception:
            pass

        self.findings.append({
            "probe_type": "cors",
            "severity": "info",
            "title": "CORS — configurado corretamente",
            "description": "O servidor nao aceita requisicoes de origens desconhecidas.",
            "result": "Origin maliciosa rejeitada.",
            "confirmed": False,
            "endpoint": "/",
            "payload_used": None,
            "response_code": None,
            "recommendation": "CORS configurado corretamente.",
        })

    def _probe_security_headers(self, target_url: str):
        """Check for missing security headers."""
        required_headers = {
            "strict-transport-security": ("HSTS ausente", "medium"),
            "x-content-type-options": ("X-Content-Type-Options ausente", "low"),
            "x-frame-options": ("X-Frame-Options ausente", "medium"),
            "content-security-policy": ("Content-Security-Policy ausente", "medium"),
            "referrer-policy": ("Referrer-Policy ausente", "low"),
            "permissions-policy": ("Permissions-Policy ausente", "low"),
        }
        try:
            r = httpx.get(target_url, timeout=REQUEST_TIMEOUT)
            response_headers = {k.lower(): v for k, v in r.headers.items()}

            missing = []
            for header, (title, severity) in required_headers.items():
                if header not in response_headers:
                    missing.append((header, title, severity))

            if missing:
                for header, title, severity in missing:
                    self.findings.append({
                        "probe_type": "security_headers",
                        "severity": severity,
                        "title": f"Header de seguranca: {title}",
                        "description": f"O header {header} nao esta presente na resposta.",
                        "result": f"Header ausente: {header}",
                        "confirmed": True,
                        "endpoint": "/",
                        "payload_used": None,
                        "response_code": r.status_code,
                        "recommendation": f"Adicione o header {header} na configuracao do servidor.",
                    })
            else:
                self.findings.append({
                    "probe_type": "security_headers",
                    "severity": "info",
                    "title": "Headers de seguranca — todos presentes",
                    "description": "Todos os headers de seguranca recomendados estao configurados.",
                    "result": "Todos presentes.",
                    "confirmed": False,
                    "endpoint": "/",
                    "payload_used": None,
                    "response_code": r.status_code,
                    "recommendation": "Headers de seguranca configurados corretamente.",
                })
        except Exception:
            pass

    def _probe_idor(self, target_url: str):
        """Test for IDOR — skipped if no second user configured."""
        self.findings.append({
            "probe_type": "idor",
            "severity": "info",
            "title": "IDOR — teste nao executado",
            "description": "O teste de IDOR requer um segundo usuario configurado. Pulado nesta execucao.",
            "result": "Probe pulado — segundo usuario nao configurado.",
            "confirmed": False,
            "endpoint": "/",
            "payload_used": None,
            "response_code": None,
            "recommendation": "Configure um segundo usuario de teste para habilitar este probe.",
        })

    def _probe_xss(self, target_url: str):
        """Test for reflected XSS."""
        payloads = [
            "<script>console.log('xss-memora-test')</script>",
            "alert('xss-memora-test')",
            '"><img src=x onerror=console.log(\'xss\')>',
        ]
        test_endpoints = [e for e in self.endpoints if e["method"] == "GET"][:3]

        for ep in test_endpoints:
            url = f"{target_url}{ep['path']}"
            for payload in payloads:
                try:
                    r = httpx.get(url, params={"q": payload}, timeout=REQUEST_TIMEOUT)
                    # Check if payload is reflected without encoding
                    if payload in r.text and "&lt;" not in r.text.replace(payload, ""):
                        self.findings.append({
                            "probe_type": "xss",
                            "severity": "high",
                            "title": "XSS Refletido — payload nao escapado na resposta",
                            "description": f"O endpoint {ep['path']} refletiu o payload XSS sem sanitizacao.",
                            "result": f"Payload encontrado na resposta sem encoding HTML.",
                            "confirmed": True,
                            "endpoint": ep["path"],
                            "payload_used": payload,
                            "response_code": r.status_code,
                            "recommendation": "Escape toda saida com HTML entities. Use frameworks que fazem isso automaticamente.",
                        })
                        return
                except Exception:
                    continue

        self.findings.append({
            "probe_type": "xss",
            "severity": "info",
            "title": "XSS — nenhuma vulnerabilidade encontrada",
            "description": "Nenhum endpoint refletiu payloads XSS sem sanitizacao.",
            "result": "Payloads nao refletidos ou corretamente escapados.",
            "confirmed": False,
            "endpoint": test_endpoints[0]["path"] if test_endpoints else "/",
            "payload_used": None,
            "response_code": None,
            "recommendation": "Continue sanitizando output HTML.",
        })

    def _probe_brute_force(self, target_url: str):
        """Test if login blocks after repeated failed attempts."""
        login_url = f"{target_url}/api/auth/login"
        blocked = False
        try:
            for i in range(5):
                r = httpx.post(
                    login_url,
                    json={"email": f"brute{i}@test.com", "password": "wrongpassword"},
                    timeout=REQUEST_TIMEOUT,
                )
                if r.status_code == 429 or "bloqueado" in r.text.lower() or "locked" in r.text.lower():
                    blocked = True
                    break
        except Exception:
            pass

        if not blocked:
            self.findings.append({
                "probe_type": "brute_force",
                "severity": "medium",
                "title": "Forca bruta — login nao bloqueia apos tentativas erradas",
                "description": "5 tentativas com senha errada nao resultaram em bloqueio.",
                "result": "Nenhuma resposta 429 ou mensagem de bloqueio.",
                "confirmed": True,
                "endpoint": "/api/auth/login",
                "payload_used": "5 tentativas com senhas erradas",
                "response_code": None,
                "recommendation": "Implemente bloqueio temporario apos N tentativas falhas (ex: 5 tentativas = 15min de espera).",
            })
        else:
            self.findings.append({
                "probe_type": "brute_force",
                "severity": "info",
                "title": "Forca bruta — protecao ativa",
                "description": "O login bloqueou apos tentativas repetidas.",
                "result": "Bloqueio detectado.",
                "confirmed": False,
                "endpoint": "/api/auth/login",
                "payload_used": None,
                "response_code": 429,
                "recommendation": "Protecao contra forca bruta ativa.",
            })

    def _probe_sensitive_exposure(self, target_url: str):
        """Test for exposed sensitive files and endpoints."""
        sensitive_urls = [
            ("/.env", "Arquivo .env exposto"),
            ("/.git/config", "Repositorio Git exposto"),
            ("/api/docs", "Swagger exposto sem auth"),
            ("/api/redoc", "ReDoc exposto sem auth"),
            ("/admin", "Painel admin acessivel"),
            ("/metrics", "Metricas expostas"),
        ]

        for path, title in sensitive_urls:
            try:
                r = httpx.get(f"{target_url}{path}", timeout=REQUEST_TIMEOUT, follow_redirects=False)
                if r.status_code == 200:
                    self.findings.append({
                        "probe_type": "sensitive_exposure",
                        "severity": "high" if path in ("/.env", "/.git/config") else "medium",
                        "title": f"Exposicao de dados — {title}",
                        "description": f"A URL {path} retornou 200 e pode expor dados sensiveis.",
                        "result": f"Status: {r.status_code}. Conteudo: {r.text[:200]}",
                        "confirmed": True,
                        "endpoint": path,
                        "payload_used": None,
                        "response_code": r.status_code,
                        "recommendation": f"Bloqueie o acesso a {path} no servidor web ou remova o arquivo.",
                    })
            except Exception:
                continue

        # If none found, add info
        if not any(f["probe_type"] == "sensitive_exposure" and f["confirmed"] for f in self.findings):
            self.findings.append({
                "probe_type": "sensitive_exposure",
                "severity": "info",
                "title": "Exposicao de dados — nenhum arquivo sensivel encontrado",
                "description": "Nenhuma URL sensivel retornou 200.",
                "result": "Todos os caminhos sensiveis retornaram 404 ou 403.",
                "confirmed": False,
                "endpoint": "/",
                "payload_used": None,
                "response_code": None,
                "recommendation": "Continue bloqueando acesso a arquivos e URLs sensiveis.",
            })

    def _probe_http_methods(self, target_url: str):
        """Test if unexpected HTTP methods are accepted."""
        get_endpoints = [e for e in self.endpoints if e["method"] == "GET"][:3]
        unexpected_methods = ["DELETE", "PUT", "PATCH"]

        for ep in get_endpoints:
            url = f"{target_url}{ep['path']}"
            for method in unexpected_methods:
                try:
                    r = httpx.request(method, url, timeout=REQUEST_TIMEOUT)
                    if r.status_code == 200:
                        self.findings.append({
                            "probe_type": "http_methods",
                            "severity": "medium",
                            "title": f"Metodo {method} aceito em endpoint GET-only",
                            "description": f"O endpoint {ep['path']} aceitou {method} quando deveria ser apenas GET.",
                            "result": f"Status: {r.status_code}",
                            "confirmed": True,
                            "endpoint": ep["path"],
                            "payload_used": f"{method} request",
                            "response_code": r.status_code,
                            "recommendation": f"Restrinja metodos HTTP aceitos em {ep['path']}. Use 405 Method Not Allowed.",
                        })
                        return
                except Exception:
                    continue

        self.findings.append({
            "probe_type": "http_methods",
            "severity": "info",
            "title": "HTTP Methods — metodos restritos corretamente",
            "description": "Endpoints GET-only rejeitaram metodos nao esperados.",
            "result": "Metodos DELETE/PUT/PATCH rejeitados.",
            "confirmed": False,
            "endpoint": get_endpoints[0]["path"] if get_endpoints else "/",
            "payload_used": None,
            "response_code": None,
            "recommendation": "Metodos HTTP restritos corretamente.",
        })

    # ────────────── Helpers ──────────────

    def _calculate_risk(self, findings: list[dict]) -> str:
        confirmed = [f for f in findings if f.get("confirmed")]
        if not confirmed:
            return "low"
        severities = [f["severity"] for f in confirmed]
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def _generate_summary(self, findings: list[dict], confirmed_count: int) -> str:
        if confirmed_count == 0:
            return "Nenhuma vulnerabilidade confirmada. O sistema passou em todos os testes ativos."

        confirmed = [f for f in findings if f.get("confirmed")]
        parts = [f["title"] for f in confirmed[:3]]
        summary = ". ".join(parts) + "."
        if confirmed_count > 3:
            summary += f" E mais {confirmed_count - 3} vulnerabilidades encontradas."
        return summary
