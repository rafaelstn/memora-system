"""Email client centralizado com templates HTML para todos os modulos."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

# ────────────── Base Template ──────────────

BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:600px;margin:20px auto;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e4e4e7;">
  <div style="background:{header_color};padding:20px 24px;">
    <table width="100%"><tr>
      <td><span style="font-size:16px;font-weight:700;color:#ffffff;">{header_icon} {header_title}</span></td>
      <td align="right"><span style="font-size:12px;color:rgba(255,255,255,0.7);">Memora</span></td>
    </tr></table>
  </div>
  <div style="padding:24px;">
    {content}
  </div>
  <div style="padding:16px 24px;background:#fafafa;border-top:1px solid #e4e4e7;text-align:center;">
    <span style="font-size:11px;color:#a1a1aa;">Memora — Inteligencia Tecnica Operacional</span>
  </div>
</div>
</body>
</html>
"""

BUTTON_HTML = '<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;margin-top:12px;">{label}</a>'

BADGE_HTML = '<span style="display:inline-block;background:{bg};color:{color};padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;text-transform:uppercase;">{text}</span>'

# ────────────── Send Function ──────────────


def send(to: str, subject: str, body_html: str) -> bool:
    """Send email via SMTP. Returns True on success."""
    smtp_host = settings.smtp_host
    smtp_port = settings.smtp_port
    smtp_user = settings.smtp_user
    smtp_password = settings.smtp_password
    smtp_from = settings.smtp_from or smtp_user

    if not smtp_host or not smtp_user:
        logger.debug("SMTP nao configurado, pulando envio")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info("Email enviado para %s: %s", to, subject[:50])
        return True
    except Exception as e:
        logger.error("Falha ao enviar email para %s: %s", to, e)
        return False


def send_to_org_admins(db: Session, org_id: str, subject: str, body_html: str, category: str = "all"):
    """Send email to all active admins in the org, respecting notification preferences."""
    admins = db.execute(
        text("""
            SELECT u.email FROM users u
            LEFT JOIN notification_preferences np ON np.user_id = u.id
            WHERE u.org_id = :org_id AND u.role = 'admin' AND u.is_active = true
            AND (np.id IS NULL OR np.email_enabled = true)
        """),
        {"org_id": org_id},
    ).mappings().all()

    sent = 0
    for admin in admins:
        if send(admin["email"], subject, body_html):
            sent += 1
    return sent


def send_to_role(db: Session, org_id: str, role: str, subject: str, body_html: str):
    """Send email to all active users with given role."""
    users = db.execute(
        text("""
            SELECT u.email FROM users u
            LEFT JOIN notification_preferences np ON np.user_id = u.id
            WHERE u.org_id = :org_id AND u.role = :role AND u.is_active = true
            AND (np.id IS NULL OR np.email_enabled = true)
        """),
        {"org_id": org_id, "role": role},
    ).mappings().all()

    sent = 0
    for user in users:
        if send(user["email"], subject, body_html):
            sent += 1
    return sent


# ────────────── Template Builders ──────────────

def _render(header_color: str, header_icon: str, header_title: str, content: str) -> str:
    return BASE_HTML.format(
        header_color=header_color,
        header_icon=header_icon,
        header_title=header_title,
        content=content,
    )


# --- Alert ---

def build_alert_email(alert: dict, project_name: str, detail_url: str) -> tuple[str, str]:
    """Build subject and HTML for an error alert."""
    emoji = {"low": "ℹ️", "medium": "⚠️", "high": "🔴", "critical": "🚨"}.get(alert.get("severity", ""), "⚠️")
    severity = alert.get("severity", "unknown").upper()
    subject = f"{emoji} [{severity}] {alert['title']} — {project_name}"

    suggested = alert.get("suggested_actions") or []
    if isinstance(suggested, str):
        import json
        try:
            suggested = json.loads(suggested)
        except Exception:
            suggested = [suggested]
    actions_html = "".join(f"<li style='margin-bottom:4px;'>{a}</li>" for a in suggested)

    severity_colors = {"LOW": "#3b82f6", "MEDIUM": "#eab308", "HIGH": "#f97316", "CRITICAL": "#ef4444"}
    badge = BADGE_HTML.format(bg=severity_colors.get(severity, "#6b7280") + "22", color=severity_colors.get(severity, "#6b7280"), text=severity)

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">{alert['title']}</h2>
    <p style="margin:4px 0;">{badge}</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Projeto:</strong> {project_name}</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Componente:</strong> {alert.get('affected_component') or 'N/A'}</p>
    <hr style="border:none;border-top:1px solid #e4e4e7;margin:16px 0;">
    <p style="color:#3f3f46;line-height:1.6;">{alert.get('explanation', '')}</p>
    {"<h3 style='margin:16px 0 8px;font-size:14px;'>O que fazer:</h3><ol style='color:#52525b;padding-left:20px;'>" + actions_html + "</ol>" if actions_html else ""}
    {BUTTON_HTML.format(url=detail_url, color="#6366f1", label="Ver no Memora")}
    """
    body = _render("#dc2626", emoji, f"Alerta — {project_name}", content)
    return subject, body


# --- Incident ---

def build_incident_declared_email(incident: dict, detail_url: str) -> tuple[str, str]:
    """Build email for new incident declaration."""
    emoji = {"low": "⚠️", "medium": "🟡", "high": "🔴", "critical": "🚨"}.get(incident.get("severity", ""), "⚠️")
    subject = f"{emoji} Incidente declarado: {incident['title']}"

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">{incident['title']}</h2>
    <p style="margin:8px 0;color:#52525b;"><strong>Severidade:</strong> {incident.get('severity', '').upper()}</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Projeto:</strong> {incident.get('project_name', 'N/A')}</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Declarado por:</strong> {incident.get('declared_by_name', 'N/A')}</p>
    {f"<p style='color:#3f3f46;margin-top:12px;'>{incident.get('description', '')}</p>" if incident.get('description') else ""}
    {BUTTON_HTML.format(url=detail_url, color="#dc2626", label="Abrir War Room")}
    """
    body = _render("#dc2626", emoji, "Incidente Declarado", content)
    return subject, body


def build_incident_resolved_email(incident: dict, detail_url: str) -> tuple[str, str]:
    """Build email for resolved incident."""
    subject = f"✅ Incidente resolvido: {incident['title']}"

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">✅ {incident['title']}</h2>
    <p style="margin:8px 0;color:#52525b;"><strong>Status:</strong> Resolvido</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Projeto:</strong> {incident.get('project_name', 'N/A')}</p>
    {f"<p style='color:#3f3f46;margin-top:12px;'><strong>Resumo:</strong> {incident.get('resolution_summary', '')}</p>" if incident.get('resolution_summary') else ""}
    {BUTTON_HTML.format(url=detail_url + "/postmortem", color="#16a34a", label="Ver Post-mortem")}
    """
    body = _render("#16a34a", "✅", "Incidente Resolvido", content)
    return subject, body


def build_incident_no_update_email(incident: dict, detail_url: str) -> tuple[str, str]:
    """Build reminder email for stale incidents."""
    subject = f"⏰ Sem atualizacao: {incident['title']}"

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">⏰ Incidente sem atualizacao</h2>
    <p style="margin:8px 0;color:#52525b;">O incidente <strong>{incident['title']}</strong> esta sem atualizacao ha mais de 1 hora.</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Status:</strong> {incident.get('status', '').upper()}</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Projeto:</strong> {incident.get('project_name', 'N/A')}</p>
    <p style="color:#71717a;margin-top:12px;">Atualize a timeline com o progresso da investigacao.</p>
    {BUTTON_HTML.format(url=detail_url, color="#f59e0b", label="Atualizar War Room")}
    """
    body = _render("#f59e0b", "⏰", "Lembrete — Incidente sem atualizacao", content)
    return subject, body


# --- Security ---

def build_security_scan_email(scan: dict, detail_url: str) -> tuple[str, str]:
    """Build email for completed security scan."""
    score = scan.get("security_score", 0)
    emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
    subject = f"{emoji} Auditoria de seguranca: {scan.get('repo_name', '')} — Score {score}/100"

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">{emoji} Score: {score}/100</h2>
    <p style="margin:8px 0;color:#52525b;"><strong>Repositorio:</strong> {scan.get('repo_name', '')}</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Criticos:</strong> {scan.get('critical_count', 0)} | <strong>Altos:</strong> {scan.get('high_count', 0)} | <strong>Medios:</strong> {scan.get('medium_count', 0)}</p>
    {BUTTON_HTML.format(url=detail_url, color="#6366f1", label="Ver Detalhes")}
    """
    body = _render("#6366f1", "🛡️", "Auditoria de Seguranca", content)
    return subject, body


# --- DAST ---

def build_dast_scan_email(scan: dict, detail_url: str) -> tuple[str, str]:
    """Build email for completed DAST scan."""
    vulns = scan.get("vulnerabilities_confirmed", 0)
    risk = scan.get("risk_level", "low")
    emoji = "🔴" if vulns > 0 else "✅"
    subject = f"{emoji} Teste ativo: {vulns} vulnerabilidades em {scan.get('target_url', '')}"

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">{emoji} {vulns} vulnerabilidades confirmadas</h2>
    <p style="margin:8px 0;color:#52525b;"><strong>URL:</strong> {scan.get('target_url', '')}</p>
    <p style="margin:8px 0;color:#52525b;"><strong>Risco:</strong> {risk.upper()}</p>
    {f"<p style='color:#3f3f46;margin-top:12px;'>{scan.get('summary', '')}</p>" if scan.get('summary') else ""}
    {BUTTON_HTML.format(url=detail_url, color="#f59e0b", label="Ver Resultado")}
    """
    body = _render("#f59e0b", "⚡", "Teste Ativo Concluido", content)
    return subject, body


# --- Review ---

def build_review_email(review: dict, detail_url: str) -> tuple[str, str]:
    """Build email for completed code review."""
    score = review.get("overall_score", 0)
    verdict = review.get("overall_verdict", "")
    emoji = "✅" if verdict in ("approved", "approved_with_warnings") else "⚠️"
    subject = f"{emoji} Code Review: {review.get('pr_title', review.get('id', '')[:8])} — {score}/100"

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">{emoji} Score: {score}/100</h2>
    <p style="margin:8px 0;color:#52525b;"><strong>Veredicto:</strong> {verdict.replace('_', ' ').title()}</p>
    {f"<p style='margin:8px 0;color:#52525b;'><strong>PR:</strong> {review.get('pr_title', '')}</p>" if review.get('pr_title') else ""}
    {f"<p style='color:#3f3f46;margin-top:12px;'>{review.get('summary', '')}</p>" if review.get('summary') else ""}
    {BUTTON_HTML.format(url=detail_url, color="#6366f1", label="Ver Review")}
    """
    body = _render("#6366f1", "📝", "Code Review Concluido", content)
    return subject, body


# --- Executive ---

def build_executive_snapshot_email(snapshot: dict, detail_url: str) -> tuple[str, str]:
    """Build email for executive snapshot."""
    score = snapshot.get("health_score", 0)
    emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
    subject = f"{emoji} Relatorio Executivo — Health Score: {score}/100"

    content = f"""
    <h2 style="margin:0 0 12px;font-size:18px;">{emoji} Health Score: {score}/100</h2>
    {f"<p style='color:#3f3f46;line-height:1.6;'>{snapshot.get('summary', '')}</p>" if snapshot.get('summary') else ""}
    {BUTTON_HTML.format(url=detail_url, color="#6366f1", label="Ver Painel Executivo")}
    """
    body = _render("#6366f1", "📊", "Relatorio Executivo Semanal", content)
    return subject, body


# --- Test email ---

def send_test_email(to: str) -> bool:
    """Send a test email to verify SMTP configuration."""
    subject = "✅ Teste de email — Memora"
    content = """
    <h2 style="margin:0 0 12px;font-size:18px;">✅ Email configurado corretamente!</h2>
    <p style="color:#52525b;">Se voce recebeu esta mensagem, o servidor SMTP do Memora esta funcionando.</p>
    """
    body = _render("#16a34a", "✅", "Teste de Email", content)
    return send(to, subject, body)
