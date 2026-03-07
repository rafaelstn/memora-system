"""Tests for PDF generation and download endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_session
from app.core.pdf_generator import PDFGenerator
from app.main import app
from tests.conftest import _fake_user


def _mock_session_with_data(main_row, findings=None, deps=None):
    session = MagicMock()

    # For the main query
    session.execute.return_value.mappings.return_value.first.return_value = main_row

    if findings is not None:
        # Chain: first call returns main, second returns findings list
        call_results = [MagicMock(), MagicMock()]
        call_results[0].mappings.return_value.first.return_value = main_row
        call_results[1].mappings.return_value.all.return_value = findings

        if deps is not None:
            call_results.append(MagicMock())
            call_results[2].mappings.return_value.all.return_value = deps

        session.execute.side_effect = call_results

    session.query.return_value.filter.return_value.first.return_value = None
    return session


# --- PDFGenerator unit tests ---


class TestPDFGeneratorPostmortem:
    def test_generates_valid_pdf_bytes(self):
        gen = PDFGenerator()
        incident = {
            "id": "inc-001",
            "title": "API fora do ar",
            "severity": "critical",
            "status": "resolved",
            "project_name": "api-backend",
            "declared_at": "2026-03-01 10:00:00",
            "resolved_at": "2026-03-01 14:00:00",
            "postmortem": "## Resumo\n\nA API ficou fora do ar por 4 horas.\n\n## Causa raiz\n\nDeploy com bug.",
        }
        pdf = gen.generate_postmortem(incident)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100
        assert pdf[:5] == b"%PDF-"

    def test_postmortem_without_markdown(self):
        gen = PDFGenerator()
        incident = {
            "id": "inc-002",
            "title": "Timeout DB",
            "severity": "high",
            "status": "open",
            "project_name": "db-service",
            "declared_at": "2026-03-01",
            "resolved_at": None,
            "postmortem": None,
        }
        pdf = gen.generate_postmortem(incident)
        assert pdf[:5] == b"%PDF-"


class TestPDFGeneratorSecurity:
    def test_generates_pdf_with_findings(self):
        gen = PDFGenerator()
        scan = {
            "id": "scan-001",
            "repo_name": "my-app",
            "security_score": 72,
            "total_findings": 3,
            "critical_count": 1,
            "high_count": 1,
            "medium_count": 1,
            "low_count": 0,
        }
        findings = [
            {"severity": "critical", "title": "SQL Injection", "description": "User input not sanitized", "recommendation": "Use parameterized queries", "file_path": "app/db.py"},
            {"severity": "high", "title": "XSS", "description": "Reflected XSS found", "recommendation": "Escape output", "file_path": None},
            {"severity": "medium", "title": "Weak password", "description": "Min length 4", "recommendation": "Require 8+", "file_path": None},
        ]
        pdf = gen.generate_security_report(scan, findings)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 200


class TestPDFGeneratorExecutive:
    def test_generates_pdf_with_health_score(self):
        gen = PDFGenerator()
        snapshot = {
            "id": "snap-001",
            "period_start": "2026-02-28",
            "period_end": "2026-03-07",
            "health_score": 85,
            "summary": "Semana estavel com melhoria no MTTR.",
            "highlights": [
                {"type": "positive", "text": "MTTR reduzido em 30%"},
                {"type": "negative", "text": "2 incidentes criticos"},
            ],
            "risks": [
                {"severity": "medium", "description": "Dependencia desatualizada", "recommendation": "Atualizar openssl"},
            ],
            "recommendations": [
                {"priority": 1, "action": "Atualizar deps", "reason": "Vulnerabilidade conhecida"},
            ],
        }
        pdf = gen.generate_executive_report(snapshot)
        assert pdf[:5] == b"%PDF-"


class TestPDFGeneratorImpact:
    def test_generates_pdf_with_findings(self):
        gen = PDFGenerator()
        analysis = {
            "id": "imp-001",
            "repo_name": "my-app",
            "change_description": "Refatorar modulo de pagamentos",
            "risk_level": "high",
            "risk_summary": "Mudanca afeta 3 regras de negocio",
        }
        findings = [
            {"finding_type": "business_rule", "severity": "high", "title": "Regra de calculo alterada", "description": "Desconto progressivo pode quebrar", "recommendation": "Testar com dados reais"},
            {"finding_type": "dependency", "severity": "medium", "title": "Modulo de fatura depende", "description": "fatura.py importa pagamentos", "recommendation": "Verificar compatibilidade"},
        ]
        pdf = gen.generate_impact_report(analysis, findings)
        assert pdf[:5] == b"%PDF-"


class TestPDFGeneratorDAST:
    def test_generates_dast_pdf(self):
        gen = PDFGenerator()
        scan = {
            "id": "dast-001",
            "target_url": "https://api.test.com",
            "target_env": "staging",
            "probes_total": 10,
            "probes_completed": 10,
            "vulnerabilities_confirmed": 2,
            "risk_level": "high",
            "summary": "2 vulnerabilidades confirmadas",
            "duration_seconds": 45,
        }
        findings = [
            {"probe_type": "sql_injection", "severity": "high", "title": "SQL Injection em /api/search", "description": "Payload aceito", "confirmed": True, "recommendation": "Sanitizar input"},
            {"probe_type": "cors", "severity": "low", "title": "CORS permissivo", "description": "Aceita qualquer origin", "confirmed": False, "recommendation": "Restringir origins"},
        ]
        pdf = gen.generate_dast_report(scan, findings)
        assert pdf[:5] == b"%PDF-"


class TestPDFGeneratorBase:
    def test_pdf_has_header_and_footer(self):
        gen = PDFGenerator()
        pdf = gen.generate("Teste", "<p>Conteudo de teste</p>", "teste.pdf")
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 100


# --- Endpoint tests ---


class TestPostmortemPDFEndpoint:
    def test_download_postmortem_pdf(self):
        incident_row = {
            "id": "inc-001",
            "org_id": "org-test-001",
            "title": "API fora do ar",
            "severity": "critical",
            "status": "resolved",
            "project_name": "backend",
            "declared_at": "2026-03-01",
            "resolved_at": "2026-03-01",
            "postmortem": "## Resumo\n\nAPI caiu.",
            "postmortem_generated_at": "2026-03-01",
            "declared_by_name": "Admin",
            "alert_id": None,
            "project_id": "proj-001",
            "declared_by": "u-001",
            "description": None,
            "mitigated_at": None,
            "resolution_summary": None,
            "share_token": None,
            "similar_incidents": None,
        }
        session = MagicMock()
        session.execute.return_value.mappings.return_value.first.return_value = incident_row
        session.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)

        res = client.get("/api/incidents/inc-001/postmortem/pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "postmortem-inc-001.pdf" in res.headers.get("content-disposition", "")
        assert res.content[:5] == b"%PDF-"

        app.dependency_overrides.clear()

    def test_postmortem_pdf_not_found(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.first.return_value = None
        session.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)

        res = client.get("/api/incidents/inc-999/postmortem/pdf")
        assert res.status_code == 404

        app.dependency_overrides.clear()


class TestExecutivePDFEndpoint:
    def test_dev_cannot_download_executive_pdf(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("dev")
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)

        res = client.get("/api/executive/snapshot/snap-001/pdf")
        assert res.status_code == 403

        app.dependency_overrides.clear()

    def test_suporte_cannot_download_executive_pdf(self):
        app.dependency_overrides[get_current_user] = lambda: _fake_user("suporte")
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)

        res = client.get("/api/executive/snapshot/snap-001/pdf")
        assert res.status_code == 403

        app.dependency_overrides.clear()
