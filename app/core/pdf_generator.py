"""Centralized PDF generator for all Memora modules."""

import io
import logging
from datetime import datetime

import markdown
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

BASE_CSS = """
@page {
    size: A4;
    margin: 2cm;
    @frame footer {
        -pdf-frame-content: page-footer;
        bottom: 0;
        margin-left: 2cm;
        margin-right: 2cm;
        height: 1.5cm;
    }
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11px;
    color: #1a1a1a;
    line-height: 1.6;
}
.header {
    border-bottom: 2px solid #333;
    padding-bottom: 12px;
    margin-bottom: 20px;
}
.header h1 {
    font-size: 20px;
    margin: 0 0 4px 0;
    color: #111;
}
.header .subtitle {
    font-size: 11px;
    color: #666;
}
.header .logo {
    font-size: 14px;
    font-weight: bold;
    color: #4f46e5;
    margin-bottom: 8px;
}
h2 {
    font-size: 15px;
    color: #222;
    margin-top: 20px;
    margin-bottom: 8px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4px;
}
h3 {
    font-size: 13px;
    color: #333;
    margin-top: 14px;
    margin-bottom: 6px;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 10px;
}
th {
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
    padding: 6px 8px;
    text-align: left;
    font-weight: bold;
}
td {
    border: 1px solid #d1d5db;
    padding: 6px 8px;
}
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
}
.badge-critical { background-color: #fecaca; color: #991b1b; }
.badge-high { background-color: #fed7aa; color: #9a3412; }
.badge-medium { background-color: #fef08a; color: #854d0e; }
.badge-low { background-color: #d1fae5; color: #065f46; }
.badge-info { background-color: #e0e7ff; color: #3730a3; }
.badge-positive { background-color: #d1fae5; color: #065f46; }
.badge-negative { background-color: #fecaca; color: #991b1b; }
.badge-neutral { background-color: #e5e7eb; color: #374151; }
.score-box {
    text-align: center;
    padding: 12px;
    margin: 10px 0;
    border: 2px solid #ddd;
    border-radius: 8px;
}
.score-box .score {
    font-size: 36px;
    font-weight: bold;
}
.score-box .label {
    font-size: 12px;
    color: #666;
}
.finding-card {
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 10px;
    margin: 8px 0;
}
.finding-card .title {
    font-weight: bold;
    margin-bottom: 4px;
}
.finding-card .desc {
    color: #4b5563;
    font-size: 10px;
}
.finding-card .rec {
    color: #1d4ed8;
    font-size: 10px;
    margin-top: 4px;
}
.meta-row {
    display: block;
    margin: 4px 0;
    font-size: 11px;
}
.meta-label {
    font-weight: bold;
    color: #555;
}
ul { padding-left: 20px; }
li { margin: 3px 0; }
code {
    background-color: #f3f4f6;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 10px;
}
pre {
    background-color: #f3f4f6;
    padding: 8px;
    border-radius: 4px;
    font-size: 9px;
    overflow: hidden;
    white-space: pre-wrap;
    word-wrap: break-word;
}
#page-footer {
    text-align: center;
    font-size: 9px;
    color: #999;
    border-top: 1px solid #ddd;
    padding-top: 4px;
}
"""


def _severity_badge(severity: str) -> str:
    css_class = f"badge-{severity}" if severity in ("critical", "high", "medium", "low", "info") else "badge-info"
    return f'<span class="badge {css_class}">{severity.upper()}</span>'


def _md_to_html(md_text: str) -> str:
    if not md_text:
        return ""
    return markdown.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])


def _now_str() -> str:
    return datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")


class PDFGenerator:
    def generate(self, title: str, content_html: str, filename: str, metadata: dict | None = None) -> bytes:
        meta = metadata or {}
        date_str = meta.get("date", _now_str())

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{BASE_CSS}</style></head>
<body>
<div class="header">
    <div class="logo">MEMORA</div>
    <h1>{title}</h1>
    <div class="subtitle">Gerado em {date_str}</div>
</div>
{content_html}
<div id="page-footer">
    Memora — Inteligencia Tecnica Operacional | Pagina <pdf:pagenumber>
</div>
</body>
</html>"""

        buffer = io.BytesIO()
        result = pisa.CreatePDF(io.StringIO(html), dest=buffer)
        if result.err:
            logger.error(f"Erro ao gerar PDF: {result.err}")
            raise RuntimeError(f"Falha na geracao do PDF: {result.err}")
        return buffer.getvalue()

    def generate_postmortem(self, incident: dict) -> bytes:
        title = f"Post-mortem — {incident.get('title', 'Incidente')}"
        severity = incident.get("severity", "medium")
        status = incident.get("status", "resolved")
        declared_at = incident.get("declared_at", "")
        resolved_at = incident.get("resolved_at", "")
        project = incident.get("project_name", "")

        duration = ""
        if declared_at and resolved_at:
            try:
                t1 = datetime.fromisoformat(str(declared_at).replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(str(resolved_at).replace("Z", "+00:00"))
                delta = t2 - t1
                hours = delta.total_seconds() / 3600
                duration = f"{hours:.1f} horas"
            except Exception:
                pass

        postmortem_html = _md_to_html(incident.get("postmortem", ""))

        meta_html = f"""
<div>
    <span class="meta-row"><span class="meta-label">Projeto:</span> {project}</span>
    <span class="meta-row"><span class="meta-label">Severidade:</span> {_severity_badge(severity)}</span>
    <span class="meta-row"><span class="meta-label">Status:</span> {status}</span>
    <span class="meta-row"><span class="meta-label">Declarado em:</span> {declared_at}</span>
    <span class="meta-row"><span class="meta-label">Resolvido em:</span> {resolved_at or 'Em andamento'}</span>
    {"<span class='meta-row'><span class='meta-label'>Duracao:</span> " + duration + "</span>" if duration else ""}
</div>
<h2>Post-mortem</h2>
{postmortem_html or '<p>Post-mortem nao gerado.</p>'}
"""
        return self.generate(title, meta_html, f"postmortem-{incident.get('id', 'unknown')}.pdf")

    def generate_security_report(self, scan: dict, findings: list[dict], dependencies: list[dict] | None = None) -> bytes:
        repo = scan.get("repo_name", "")
        title = f"Relatorio de Seguranca — {repo}"
        score = scan.get("security_score")

        score_html = ""
        if score is not None:
            color = "#16a34a" if score >= 80 else "#ca8a04" if score >= 50 else "#dc2626"
            score_html = f"""
<div class="score-box">
    <div class="score" style="color: {color}">{score}/100</div>
    <div class="label">Score de Seguranca</div>
</div>"""

        summary_html = f"""
<span class="meta-row"><span class="meta-label">Repositorio:</span> {repo}</span>
<span class="meta-row"><span class="meta-label">Total de findings:</span> {scan.get('total_findings', 0)}</span>
<span class="meta-row"><span class="meta-label">Criticos:</span> {scan.get('critical_count', 0)} | <span class="meta-label">Altos:</span> {scan.get('high_count', 0)} | <span class="meta-label">Medios:</span> {scan.get('medium_count', 0)} | <span class="meta-label">Baixos:</span> {scan.get('low_count', 0)}</span>
"""

        findings_html = ""
        if findings:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.get("severity", "info"), 5))
            for f in sorted_findings:
                rec = f"<div class='rec'>Recomendacao: {f['recommendation']}</div>" if f.get("recommendation") else ""
                file_info = f" ({f['file_path']})" if f.get("file_path") else ""
                findings_html += f"""
<div class="finding-card">
    <div class="title">{_severity_badge(f.get('severity', 'info'))} {f.get('title', '')}{file_info}</div>
    <div class="desc">{f.get('description', '')}</div>
    {rec}
</div>"""

        deps_html = ""
        if dependencies:
            deps_html = "<h2>Dependencias Vulneraveis</h2><table><tr><th>Pacote</th><th>Versao</th><th>Severidade</th><th>Correcao</th></tr>"
            for d in dependencies:
                deps_html += f"<tr><td>{d.get('package_name', '')}</td><td>{d.get('current_version', '—')}</td><td>{_severity_badge(d.get('severity', 'low'))}</td><td>{d.get('fixed_version', '—')}</td></tr>"
            deps_html += "</table>"

        content = f"""
{score_html}
{summary_html}
<h2>Findings</h2>
{findings_html or '<p>Nenhum finding encontrado.</p>'}
{deps_html}
"""
        return self.generate(title, content, f"security-{scan.get('id', 'unknown')}.pdf")

    def generate_executive_report(self, snapshot: dict) -> bytes:
        period_start = snapshot.get("period_start", "")
        period_end = snapshot.get("period_end", "")
        title = f"Relatorio Executivo — {period_start[:10] if period_start else ''} a {period_end[:10] if period_end else ''}"

        health = snapshot.get("health_score", 0)
        color = "#16a34a" if health >= 80 else "#ca8a04" if health >= 50 else "#dc2626"

        score_html = f"""
<div class="score-box">
    <div class="score" style="color: {color}">{health}/100</div>
    <div class="label">Health Score</div>
</div>"""

        summary_html = _md_to_html(snapshot.get("summary", "")) if snapshot.get("summary") else ""

        highlights_html = ""
        highlights = snapshot.get("highlights", [])
        if highlights:
            highlights_html = "<h2>Destaques</h2><ul>"
            for h in highlights:
                badge = f"badge-{h.get('type', 'neutral')}"
                highlights_html += f'<li><span class="badge {badge}">{h.get("type", "").upper()}</span> {h.get("text", "")}</li>'
            highlights_html += "</ul>"

        risks_html = ""
        risks = snapshot.get("risks", [])
        if risks:
            risks_html = "<h2>Riscos</h2>"
            for r in risks:
                risks_html += f"""
<div class="finding-card">
    <div class="title">{_severity_badge(r.get('severity', 'low'))} {r.get('description', '')}</div>
    <div class="rec">Recomendacao: {r.get('recommendation', '')}</div>
</div>"""

        recs_html = ""
        recs = snapshot.get("recommendations", [])
        if recs:
            recs_html = "<h2>Recomendacoes</h2><table><tr><th>#</th><th>Acao</th><th>Motivo</th></tr>"
            for rec in recs:
                recs_html += f"<tr><td>{rec.get('priority', '')}</td><td>{rec.get('action', '')}</td><td>{rec.get('reason', '')}</td></tr>"
            recs_html += "</table>"

        content = f"""
{score_html}
{f"<h2>Resumo</h2>{summary_html}" if summary_html else ""}
{highlights_html}
{risks_html}
{recs_html}
"""
        return self.generate(title, content, f"executive-{snapshot.get('id', 'unknown')}.pdf")

    def generate_impact_report(self, analysis: dict, findings: list[dict]) -> bytes:
        desc = analysis.get("change_description", "")[:50]
        title = f"Analise de Impacto — {desc}"
        risk = analysis.get("risk_level", "low")

        risk_html = f"""
<div class="score-box">
    <div class="score">{_severity_badge(risk)}</div>
    <div class="label">Nivel de Risco</div>
</div>"""

        meta_html = f"""
<span class="meta-row"><span class="meta-label">Repositorio:</span> {analysis.get('repo_name', '')}</span>
<span class="meta-row"><span class="meta-label">Descricao:</span> {analysis.get('change_description', '')}</span>
<span class="meta-row"><span class="meta-label">Resumo do risco:</span> {analysis.get('risk_summary', '—')}</span>
"""

        findings_by_type: dict[str, list] = {}
        for f in findings:
            ft = f.get("finding_type", "other")
            findings_by_type.setdefault(ft, []).append(f)

        type_labels = {
            "dependency": "Dependencias",
            "business_rule": "Regras de Negocio",
            "pattern_break": "Quebra de Padrao",
            "similar_change": "Mudancas Similares",
        }

        findings_html = ""
        for ft, items in findings_by_type.items():
            label = type_labels.get(ft, ft.replace("_", " ").title())
            findings_html += f"<h3>{label}</h3>"
            for f in items:
                rec = f"<div class='rec'>Recomendacao: {f['recommendation']}</div>" if f.get("recommendation") else ""
                findings_html += f"""
<div class="finding-card">
    <div class="title">{_severity_badge(f.get('severity', 'low'))} {f.get('title', '')}</div>
    <div class="desc">{f.get('description', '')}</div>
    {rec}
</div>"""

        content = f"""
{risk_html}
{meta_html}
<h2>Findings</h2>
{findings_html or '<p>Nenhum finding encontrado.</p>'}
"""
        return self.generate(title, content, f"impact-{analysis.get('id', 'unknown')}.pdf")

    def generate_dast_report(self, scan: dict, findings: list[dict]) -> bytes:
        target = scan.get("target_url", "")
        title = f"Relatorio de Teste Ativo — {target}"
        risk = scan.get("risk_level", "low")
        confirmed = scan.get("vulnerabilities_confirmed", 0)

        risk_html = f"""
<div class="score-box">
    <div class="score">{_severity_badge(risk or 'low')}</div>
    <div class="label">Nivel de Risco — {confirmed} vulnerabilidade(s) confirmada(s)</div>
</div>"""

        meta_html = f"""
<span class="meta-row"><span class="meta-label">Alvo:</span> {target}</span>
<span class="meta-row"><span class="meta-label">Ambiente:</span> {scan.get('target_env', '')}</span>
<span class="meta-row"><span class="meta-label">Probes:</span> {scan.get('probes_completed', 0)}/{scan.get('probes_total', 0)}</span>
<span class="meta-row"><span class="meta-label">Duracao:</span> {scan.get('duration_seconds', 0)}s</span>
"""

        if scan.get("summary"):
            meta_html += f"<p>{scan['summary']}</p>"

        findings_html = ""
        if findings:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.get("severity", "info"), 5))
            for f in sorted_findings:
                confirmed_badge = ' <span class="badge badge-critical">CONFIRMADO</span>' if f.get("confirmed") else ""
                rec = f"<div class='rec'>Recomendacao: {f['recommendation']}</div>" if f.get("recommendation") else ""
                findings_html += f"""
<div class="finding-card">
    <div class="title">{_severity_badge(f.get('severity', 'info'))} {f.get('title', '')}{confirmed_badge}</div>
    <div class="desc">{f.get('description', '')}</div>
    {rec}
</div>"""

        content = f"""
{risk_html}
{meta_html}
<h2>Resultados dos Probes</h2>
{findings_html or '<p>Nenhuma vulnerabilidade encontrada.</p>'}
"""
        return self.generate(title, content, f"dast-{scan.get('id', 'unknown')}.pdf")
