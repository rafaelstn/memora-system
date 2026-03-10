"""Gerador de digest semanal por email para o Memora."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────
# 1. Coleta de metricas da semana
# ────────────────────────────────────────────


def generate_digest(
    db: Session,
    org_id: str,
    product_id: str,
    week_start: datetime,
    week_end: datetime,
) -> dict:
    """Consulta o banco e retorna metricas agregadas da semana para um produto."""

    params = {
        "org_id": org_id,
        "product_id": product_id,
        "week_start": week_start,
        "week_end": week_end,
    }

    digest: dict = {}

    # ── Assistente de Suporte ──────────────────────────────

    try:
        total_questions = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.org_id = :org_id
                  AND c.product_id = :product_id
                  AND m.role = 'user'
                  AND m.created_at >= :week_start
                  AND m.created_at < :week_end
            """),
            params,
        ).scalar() or 0

        top_users_rows = db.execute(
            text("""
                SELECT u.email, COUNT(*) AS qtd
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                JOIN users u ON u.id = c.user_id
                WHERE c.org_id = :org_id
                  AND c.product_id = :product_id
                  AND m.role = 'user'
                  AND m.created_at >= :week_start
                  AND m.created_at < :week_end
                GROUP BY u.email
                ORDER BY qtd DESC
                LIMIT 5
            """),
            params,
        ).mappings().all()

        unanswered = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.org_id = :org_id
                  AND c.product_id = :product_id
                  AND m.role = 'user'
                  AND m.created_at >= :week_start
                  AND m.created_at < :week_end
                  AND m.feedback = 'negative'
            """),
            params,
        ).scalar() or 0

        if total_questions > 0:
            digest["suporte"] = {
                "total_perguntas": total_questions,
                "top_usuarios": [
                    {"email": r["email"], "perguntas": r["qtd"]} for r in top_users_rows
                ],
                "respostas_insatisfatorias": unanswered,
            }
    except Exception as exc:
        logger.warning("Erro ao coletar metricas de suporte: %s", exc)

    # ── Monitor de Erros ──────────────────────────────────

    try:
        alert_row = db.execute(
            text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE ea.severity = 'critical') AS critical,
                    COUNT(*) FILTER (WHERE ea.severity IN ('medium', 'high')) AS warning
                FROM error_alerts ea
                JOIN monitored_projects mp ON mp.id = ea.project_id
                WHERE mp.org_id = :org_id
                  AND mp.product_id = :product_id
                  AND ea.created_at >= :week_start
                  AND ea.created_at < :week_end
            """),
            params,
        ).mappings().first()

        avg_resolution = db.execute(
            text("""
                SELECT AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.created_at)) / 3600)
                    AS avg_hours
                FROM incidents i
                JOIN monitored_projects mp ON mp.id = i.project_id
                WHERE mp.org_id = :org_id
                  AND mp.product_id = :product_id
                  AND i.status = 'resolved'
                  AND i.resolved_at >= :week_start
                  AND i.resolved_at < :week_end
            """),
            params,
        ).scalar()

        total_alerts = alert_row["total"] if alert_row else 0
        if total_alerts > 0 or avg_resolution is not None:
            digest["monitor"] = {
                "total_alertas": total_alerts,
                "criticos": alert_row["critical"] if alert_row else 0,
                "avisos": alert_row["warning"] if alert_row else 0,
                "tempo_medio_resolucao_h": round(avg_resolution, 1) if avg_resolution else None,
            }
    except Exception as exc:
        logger.warning("Erro ao coletar metricas de monitor: %s", exc)

    # ── Revisao de Codigo ──────────────────────────────────

    try:
        review_row = db.execute(
            text("""
                SELECT
                    COUNT(*) AS total_reviews,
                    AVG(cr.overall_score) AS avg_score
                FROM code_reviews cr
                WHERE cr.org_id = :org_id
                  AND cr.product_id = :product_id
                  AND cr.created_at >= :week_start
                  AND cr.created_at < :week_end
            """),
            params,
        ).mappings().first()

        critical_findings = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM review_findings rf
                JOIN code_reviews cr ON cr.id = rf.review_id
                WHERE cr.org_id = :org_id
                  AND cr.product_id = :product_id
                  AND rf.severity = 'critical'
                  AND cr.created_at >= :week_start
                  AND cr.created_at < :week_end
            """),
            params,
        ).scalar() or 0

        total_reviews = review_row["total_reviews"] if review_row else 0
        if total_reviews > 0:
            digest["revisao"] = {
                "prs_revisados": total_reviews,
                "score_medio": round(float(review_row["avg_score"]), 1) if review_row and review_row["avg_score"] else None,
                "findings_criticos": critical_findings,
            }
    except Exception as exc:
        logger.warning("Erro ao coletar metricas de revisao: %s", exc)

    # ── Memoria Tecnica ──────────────────────────────────

    try:
        new_entries = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM knowledge_entries ke
                WHERE ke.org_id = :org_id
                  AND ke.product_id = :product_id
                  AND ke.created_at >= :week_start
                  AND ke.created_at < :week_end
            """),
            params,
        ).scalar() or 0

        docs_processed = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM knowledge_documents kd
                WHERE kd.org_id = :org_id
                  AND kd.product_id = :product_id
                  AND kd.status = 'completed'
                  AND kd.created_at >= :week_start
                  AND kd.created_at < :week_end
            """),
            params,
        ).scalar() or 0

        if new_entries > 0 or docs_processed > 0:
            digest["memoria"] = {
                "novos_conhecimentos": new_entries,
                "documentos_processados": docs_processed,
            }
    except Exception as exc:
        logger.warning("Erro ao coletar metricas de memoria tecnica: %s", exc)

    # ── Seguranca ──────────────────────────────────

    try:
        sast_count = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM security_scans ss
                WHERE ss.org_id = :org_id
                  AND ss.product_id = :product_id
                  AND ss.status = 'completed'
                  AND ss.created_at >= :week_start
                  AND ss.created_at < :week_end
            """),
            params,
        ).scalar() or 0

        dast_count = db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM dast_scans ds
                WHERE ds.org_id = :org_id
                  AND ds.product_id = :product_id
                  AND ds.status = 'completed'
                  AND ds.created_at >= :week_start
                  AND ds.created_at < :week_end
            """),
            params,
        ).scalar() or 0

        vuln_row = db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE sf.severity = 'critical') AS critical,
                    COUNT(*) FILTER (WHERE sf.severity = 'high') AS high,
                    COUNT(*) FILTER (WHERE sf.severity = 'medium') AS medium,
                    COUNT(*) FILTER (WHERE sf.severity = 'low') AS low
                FROM security_findings sf
                JOIN security_scans ss ON ss.id = sf.scan_id
                WHERE ss.org_id = :org_id
                  AND ss.product_id = :product_id
                  AND ss.created_at >= :week_start
                  AND ss.created_at < :week_end
            """),
            params,
        ).mappings().first()

        total_scans = sast_count + dast_count
        if total_scans > 0:
            digest["seguranca"] = {
                "scans_executados": total_scans,
                "sast": sast_count,
                "dast": dast_count,
                "vulnerabilidades": {
                    "criticas": vuln_row["critical"] if vuln_row else 0,
                    "altas": vuln_row["high"] if vuln_row else 0,
                    "medias": vuln_row["medium"] if vuln_row else 0,
                    "baixas": vuln_row["low"] if vuln_row else 0,
                },
            }
    except Exception as exc:
        logger.warning("Erro ao coletar metricas de seguranca: %s", exc)

    return digest


# ────────────────────────────────────────────
# 2. Renderizacao do email HTML
# ────────────────────────────────────────────

_SECTION_STYLE = (
    "margin:0 0 24px;padding:16px;background:#fafafa;"
    "border:1px solid #e4e4e7;border-radius:8px;"
)
_H3_STYLE = "margin:0 0 12px;font-size:15px;color:#18181b;"
_METRIC_STYLE = "margin:4px 0;font-size:14px;color:#3f3f46;"
_SUBTLE_STYLE = "font-size:12px;color:#71717a;"


def _fmt_date(dt: datetime) -> str:
    """Formata data como DD/MM/YYYY."""
    return dt.strftime("%d/%m/%Y")


def render_digest_email(
    org_name: str,
    digest_data: dict,
    week_start: datetime,
    week_end: datetime,
    dashboard_url: str,
) -> tuple[str, str]:
    """Retorna (subject, html_body) do digest semanal."""

    subject = (
        f"Resumo semanal do Memora — {org_name} "
        f"— semana de {_fmt_date(week_start)}"
    )

    sections_html = ""

    # ── Suporte ──
    sup = digest_data.get("suporte")
    if sup:
        top_html = ""
        for u in sup.get("top_usuarios", []):
            top_html += f"<li style='{_METRIC_STYLE}'>{u['email']} — {u['perguntas']} perguntas</li>"
        if top_html:
            top_html = f"<ul style='padding-left:18px;margin:8px 0 0;'>{top_html}</ul>"

        sections_html += f"""
        <div style="{_SECTION_STYLE}">
            <h3 style="{_H3_STYLE}">💬 Assistente de Suporte</h3>
            <p style="{_METRIC_STYLE}"><strong>{sup['total_perguntas']}</strong> perguntas recebidas</p>
            <p style="{_METRIC_STYLE}"><strong>{sup['respostas_insatisfatorias']}</strong> respostas insatisfatorias</p>
            {top_html}
        </div>
        """

    # ── Monitor ──
    mon = digest_data.get("monitor")
    if mon:
        resolucao = (
            f"<p style='{_METRIC_STYLE}'>Tempo medio de resolucao: <strong>{mon['tempo_medio_resolucao_h']}h</strong></p>"
            if mon.get("tempo_medio_resolucao_h") is not None
            else ""
        )
        sections_html += f"""
        <div style="{_SECTION_STYLE}">
            <h3 style="{_H3_STYLE}">🚨 Monitor de Erros</h3>
            <p style="{_METRIC_STYLE}"><strong>{mon['total_alertas']}</strong> alertas no periodo</p>
            <p style="{_METRIC_STYLE}">Criticos: <strong>{mon['criticos']}</strong> | Avisos: <strong>{mon['avisos']}</strong></p>
            {resolucao}
        </div>
        """

    # ── Revisao ──
    rev = digest_data.get("revisao")
    if rev:
        score_txt = f"{rev['score_medio']}/100" if rev.get("score_medio") is not None else "N/A"
        sections_html += f"""
        <div style="{_SECTION_STYLE}">
            <h3 style="{_H3_STYLE}">📝 Revisao de Codigo</h3>
            <p style="{_METRIC_STYLE}"><strong>{rev['prs_revisados']}</strong> PRs revisados</p>
            <p style="{_METRIC_STYLE}">Score medio: <strong>{score_txt}</strong></p>
            <p style="{_METRIC_STYLE}">Findings criticos: <strong>{rev['findings_criticos']}</strong></p>
        </div>
        """

    # ── Memoria ──
    mem = digest_data.get("memoria")
    if mem:
        sections_html += f"""
        <div style="{_SECTION_STYLE}">
            <h3 style="{_H3_STYLE}">🧠 Memoria Tecnica</h3>
            <p style="{_METRIC_STYLE}"><strong>{mem['novos_conhecimentos']}</strong> novos conhecimentos registrados</p>
            <p style="{_METRIC_STYLE}"><strong>{mem['documentos_processados']}</strong> documentos processados</p>
        </div>
        """

    # ── Seguranca ──
    sec = digest_data.get("seguranca")
    if sec:
        v = sec.get("vulnerabilidades", {})
        sections_html += f"""
        <div style="{_SECTION_STYLE}">
            <h3 style="{_H3_STYLE}">🛡️ Seguranca</h3>
            <p style="{_METRIC_STYLE}"><strong>{sec['scans_executados']}</strong> scans executados (SAST: {sec['sast']}, DAST: {sec['dast']})</p>
            <p style="{_METRIC_STYLE}">
                Vulnerabilidades — Criticas: <strong>{v.get('criticas', 0)}</strong>
                | Altas: <strong>{v.get('altas', 0)}</strong>
                | Medias: <strong>{v.get('medias', 0)}</strong>
                | Baixas: <strong>{v.get('baixas', 0)}</strong>
            </p>
        </div>
        """

    # ── Sem dados ──
    if not sections_html:
        sections_html = f"""
        <div style="{_SECTION_STYLE}">
            <p style="{_METRIC_STYLE}">Nenhuma atividade registrada nesta semana.</p>
        </div>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="max-width:600px;margin:20px auto;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e4e4e7;">

        <div style="background:#6366f1;padding:20px 24px;">
            <table width="100%"><tr>
                <td><span style="font-size:16px;font-weight:700;color:#ffffff;">📊 Resumo Semanal</span></td>
                <td align="right"><span style="font-size:12px;color:rgba(255,255,255,0.7);">Memora</span></td>
            </tr></table>
        </div>

        <div style="padding:24px;">
            <h2 style="margin:0 0 4px;font-size:18px;color:#18181b;">{org_name}</h2>
            <p style="{_SUBTLE_STYLE}">Semana de {_fmt_date(week_start)} a {_fmt_date(week_end)}</p>

            <hr style="border:none;border-top:1px solid #e4e4e7;margin:16px 0;">

            {sections_html}

            <div style="text-align:center;margin-top:24px;">
                <a href="{dashboard_url}" style="display:inline-block;background:#6366f1;color:#ffffff;padding:10px 24px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;">
                    Abrir Dashboard
                </a>
            </div>
        </div>

        <div style="padding:16px 24px;background:#fafafa;border-top:1px solid #e4e4e7;text-align:center;">
            <span style="font-size:11px;color:#a1a1aa;">Memora — Inteligencia Tecnica Operacional</span>
        </div>
    </div>
    </body>
    </html>
    """

    return subject, html_body


# ────────────────────────────────────────────
# 3. Envio do digest semanal
# ────────────────────────────────────────────


def send_weekly_digest(db: Session, org_id: str) -> str:
    """Gera e envia o digest semanal para todos os admins da organizacao.

    Retorna string de status: 'sent', 'failed', 'skipped'.
    """
    from app.core.email_client import send_to_org_admins

    # Periodo: semana anterior (segunda a domingo)
    today = datetime.utcnow().date()
    week_end_date = today - timedelta(days=today.weekday())  # segunda atual
    week_start_date = week_end_date - timedelta(days=7)
    week_start = datetime.combine(week_start_date, datetime.min.time())
    week_end = datetime.combine(week_end_date, datetime.min.time())

    status = "skipped"
    digest_id = str(uuid.uuid4())

    try:
        # Info da organizacao
        org_row = db.execute(
            text("SELECT id, name FROM organizations WHERE id = :org_id"),
            {"org_id": org_id},
        ).mappings().first()

        if not org_row:
            logger.warning("Organizacao %s nao encontrada para digest", org_id)
            _record_digest_log(db, digest_id, org_id, None, week_start, week_end, "failed", "Organizacao nao encontrada")
            return "failed"

        org_name = org_row["name"]

        # Buscar produtos ativos da organizacao
        products = db.execute(
            text("""
                SELECT id, name FROM products
                WHERE org_id = :org_id AND is_active = true
                ORDER BY name
            """),
            {"org_id": org_id},
        ).mappings().all()

        if not products:
            logger.info("Nenhum produto ativo para org %s, pulando digest", org_id)
            _record_digest_log(db, digest_id, org_id, None, week_start, week_end, "skipped", "Nenhum produto ativo")
            return "skipped"

        # Gerar digest combinado de todos os produtos
        combined_digest: dict = {}
        product_names: list[str] = []

        for product in products:
            product_digest = generate_digest(
                db, org_id, product["id"], week_start, week_end,
            )
            if product_digest:
                product_names.append(product["name"])
                _merge_digests(combined_digest, product_digest)

        if not combined_digest:
            logger.info("Sem atividade na semana para org %s, pulando digest", org_id)
            _record_digest_log(db, digest_id, org_id, None, week_start, week_end, "skipped", "Sem atividade na semana")
            return "skipped"

        dashboard_url = f"{settings.app_url}/dashboard"

        subject, html_body = render_digest_email(
            org_name=org_name,
            digest_data=combined_digest,
            week_start=week_start,
            week_end=week_end,
            dashboard_url=dashboard_url,
        )

        sent_count = send_to_org_admins(db, org_id, subject, html_body, category="digest")

        if sent_count > 0:
            status = "sent"
            logger.info(
                "Digest semanal enviado para %d admins da org %s (%s)",
                sent_count, org_id, org_name,
            )
        else:
            status = "failed"
            logger.warning("Nenhum email enviado para digest da org %s", org_id)

        _record_digest_log(
            db, digest_id, org_id,
            ",".join(p["id"] for p in products),
            week_start, week_end, status,
            f"{sent_count} emails enviados" if sent_count > 0 else "Nenhum admin com email habilitado",
        )

    except Exception as exc:
        status = "failed"
        logger.error("Erro ao gerar digest semanal para org %s: %s", org_id, exc)
        _record_digest_log(db, digest_id, org_id, None, week_start, week_end, "failed", str(exc))

    return status


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────


def _merge_digests(target: dict, source: dict) -> None:
    """Combina metricas de multiplos produtos em um unico digest."""
    for section, data in source.items():
        if section not in target:
            target[section] = data
            continue

        existing = target[section]

        if section == "suporte":
            existing["total_perguntas"] += data["total_perguntas"]
            existing["respostas_insatisfatorias"] += data["respostas_insatisfatorias"]
            # Combina top usuarios mantendo os 5 maiores
            all_users = existing.get("top_usuarios", []) + data.get("top_usuarios", [])
            merged: dict[str, int] = {}
            for u in all_users:
                merged[u["email"]] = merged.get(u["email"], 0) + u["perguntas"]
            existing["top_usuarios"] = sorted(
                [{"email": k, "perguntas": v} for k, v in merged.items()],
                key=lambda x: x["perguntas"],
                reverse=True,
            )[:5]

        elif section == "monitor":
            existing["total_alertas"] += data["total_alertas"]
            existing["criticos"] += data["criticos"]
            existing["avisos"] += data["avisos"]
            # Media ponderada de resolucao (simplificado: pega o menor)
            if data.get("tempo_medio_resolucao_h") is not None:
                if existing.get("tempo_medio_resolucao_h") is not None:
                    existing["tempo_medio_resolucao_h"] = round(
                        (existing["tempo_medio_resolucao_h"] + data["tempo_medio_resolucao_h"]) / 2, 1,
                    )
                else:
                    existing["tempo_medio_resolucao_h"] = data["tempo_medio_resolucao_h"]

        elif section == "revisao":
            total_existing = existing["prs_revisados"]
            total_new = data["prs_revisados"]
            combined_total = total_existing + total_new
            # Media ponderada do score
            if existing.get("score_medio") is not None and data.get("score_medio") is not None:
                existing["score_medio"] = round(
                    (existing["score_medio"] * total_existing + data["score_medio"] * total_new) / combined_total, 1,
                )
            elif data.get("score_medio") is not None:
                existing["score_medio"] = data["score_medio"]
            existing["prs_revisados"] = combined_total
            existing["findings_criticos"] += data["findings_criticos"]

        elif section == "memoria":
            existing["novos_conhecimentos"] += data["novos_conhecimentos"]
            existing["documentos_processados"] += data["documentos_processados"]

        elif section == "seguranca":
            existing["scans_executados"] += data["scans_executados"]
            existing["sast"] += data["sast"]
            existing["dast"] += data["dast"]
            ev = existing.get("vulnerabilidades", {})
            dv = data.get("vulnerabilidades", {})
            for key in ("criticas", "altas", "medias", "baixas"):
                ev[key] = ev.get(key, 0) + dv.get(key, 0)
            existing["vulnerabilidades"] = ev


def _record_digest_log(
    db: Session,
    digest_id: str,
    org_id: str,
    product_ids: str | None,
    week_start: datetime,
    week_end: datetime,
    status: str,
    details: str | None = None,
) -> None:
    """Registra o resultado do envio na tabela weekly_digest_log."""
    try:
        db.execute(
            text("""
                INSERT INTO weekly_digest_log (id, org_id, product_ids, week_start, week_end, status, details, created_at)
                VALUES (:id, :org_id, :product_ids, :week_start, :week_end, :status, :details, NOW())
            """),
            {
                "id": digest_id,
                "org_id": org_id,
                "product_ids": product_ids,
                "week_start": week_start,
                "week_end": week_end,
                "status": status,
                "details": details,
            },
        )
        db.commit()
    except Exception as exc:
        logger.warning("Falha ao registrar digest log: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
