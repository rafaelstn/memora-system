"""Exportador de dados do Memora — JSON e CSV ZIP."""
import csv
import io
import json
import logging
import os
import uuid
import zipfile
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "exports")
EXPORT_EXPIRY_DAYS = 7

# Tabelas exportaveis e suas queries
EXPORTABLE_TABLES = {
    "conversations": {
        "query": """
            SELECT c.id, c.title, c.repo_name, c.user_id, c.created_at, c.updated_at
            FROM conversations c
            WHERE c.org_id = :org_id {product_filter} {period_filter}
            ORDER BY c.created_at DESC
        """,
        "has_product_id": True,
    },
    "messages": {
        "query": """
            SELECT m.id, m.conversation_id, m.role, m.content, m.model_used,
                   m.tokens_used, m.cost_usd, m.created_at
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.org_id = :org_id {product_filter} {period_filter_m}
            ORDER BY m.created_at DESC
        """,
        "has_product_id": True,
        "period_col": "m.created_at",
    },
    "business_rules": {
        "query": """
            SELECT id, title, description, plain_english, rule_type, confidence,
                   is_active, extracted_at, created_at, updated_at
            FROM business_rules
            WHERE org_id = :org_id {product_filter} {period_filter}
            ORDER BY created_at DESC
        """,
        "has_product_id": True,
    },
    "knowledge_entries": {
        "query": """
            SELECT id, title, content, summary, source_type, source_url,
                   decision_type, extracted_at, source_date, created_at
            FROM knowledge_entries
            WHERE org_id = :org_id {product_filter} {period_filter}
            ORDER BY created_at DESC
        """,
        "has_product_id": True,
    },
    "knowledge_documents": {
        "query": """
            SELECT id, file_name, file_type, file_size_bytes, status,
                   summary, page_count, created_at
            FROM knowledge_documents
            WHERE org_id = :org_id {product_filter} {period_filter}
            ORDER BY created_at DESC
        """,
        "has_product_id": True,
    },
    "knowledge_wikis": {
        "query": """
            SELECT id, component_name, component_path, content,
                   last_generated_at, generation_version, created_at
            FROM knowledge_wikis
            WHERE org_id = :org_id {period_filter}
            ORDER BY created_at DESC
        """,
        "has_product_id": False,
    },
    "code_reviews": {
        "query": """
            SELECT id, source_type, repo_name, pr_number, pr_title,
                   overall_score, verdict, summary, status, created_at
            FROM code_reviews
            WHERE org_id = :org_id {product_filter} {period_filter}
            ORDER BY created_at DESC
        """,
        "has_product_id": True,
    },
    "review_findings": {
        "query": """
            SELECT rf.id, rf.review_id, rf.category, rf.severity, rf.title,
                   rf.description, rf.suggestion, rf.file_path, rf.created_at
            FROM review_findings rf
            WHERE rf.org_id = :org_id {period_filter_rf}
            ORDER BY rf.created_at DESC
        """,
        "has_product_id": False,
        "period_col": "rf.created_at",
    },
    "error_alerts": {
        "query": """
            SELECT ea.id, ea.title, ea.explanation, ea.severity, ea.status,
                   ea.affected_component, ea.created_at
            FROM error_alerts ea
            WHERE ea.org_id = :org_id {period_filter_ea}
            ORDER BY ea.created_at DESC
        """,
        "has_product_id": False,
        "period_col": "ea.created_at",
    },
    "incidents": {
        "query": """
            SELECT id, title, description, severity, status, source,
                   created_at, resolved_at
            FROM incidents
            WHERE org_id = :org_id {period_filter}
            ORDER BY created_at DESC
        """,
        "has_product_id": False,
    },
    "incident_timeline": {
        "query": """
            SELECT it.id, it.incident_id, it.event_type, it.content,
                   it.author_id, it.created_at
            FROM incident_timeline it
            JOIN incidents i ON i.id = it.incident_id
            WHERE i.org_id = :org_id {period_filter_it}
            ORDER BY it.created_at DESC
        """,
        "has_product_id": False,
        "period_col": "it.created_at",
    },
    "repo_docs": {
        "query": """
            SELECT id, repo_name, doc_type, content, generated_at, created_at
            FROM repo_docs
            WHERE org_id = :org_id {period_filter}
            ORDER BY created_at DESC
        """,
        "has_product_id": False,
    },
    "executive_weekly_snapshots": {
        "query": """
            SELECT id, week_start, week_end, security_score_avg, error_alert_count,
                   support_question_count, code_review_score_avg, prs_reviewed_count,
                   incident_resolution_avg_hours, doc_coverage_pct, created_at
            FROM executive_weekly_snapshots
            WHERE org_id = :org_id {product_filter} {period_filter}
            ORDER BY week_start DESC
        """,
        "has_product_id": True,
    },
}


def _build_query(table_config: dict, product_id: str | None, period_start: str | None, period_end: str | None) -> str:
    """Constroi query com filtros opcionais."""
    q = table_config["query"]
    period_col = table_config.get("period_col", "created_at")

    # Product filter
    if product_id and table_config.get("has_product_id"):
        product_filter = "AND product_id = :product_id"
    else:
        product_filter = ""

    # Period filter — handle different column aliases
    period_parts = []
    if period_start:
        period_parts.append(f"AND {period_col} >= :period_start")
    if period_end:
        period_parts.append(f"AND {period_col} <= :period_end")
    period_filter = " ".join(period_parts)

    # Replace all variants of period_filter placeholders
    q = q.replace("{product_filter}", product_filter)
    q = q.replace("{period_filter_m}", period_filter.replace("created_at", "m.created_at") if "m.created_at" not in period_filter else period_filter)
    q = q.replace("{period_filter_rf}", period_filter.replace("created_at", "rf.created_at") if "rf.created_at" not in period_filter else period_filter)
    q = q.replace("{period_filter_ea}", period_filter.replace("created_at", "ea.created_at") if "ea.created_at" not in period_filter else period_filter)
    q = q.replace("{period_filter_it}", period_filter.replace("created_at", "it.created_at") if "it.created_at" not in period_filter else period_filter)
    q = q.replace("{period_filter}", period_filter)

    return q


def _fetch_table_data(
    db: Session,
    table_name: str,
    org_id: str,
    product_id: str | None,
    period_start: str | None,
    period_end: str | None,
) -> list[dict]:
    """Busca dados de uma tabela com filtros."""
    config = EXPORTABLE_TABLES[table_name]
    query = _build_query(config, product_id, period_start, period_end)

    params: dict = {"org_id": org_id}
    if product_id and config.get("has_product_id"):
        params["product_id"] = product_id
    if period_start:
        params["period_start"] = period_start
    if period_end:
        params["period_end"] = period_end

    rows = db.execute(text(query), params).mappings().all()

    # Serialize datetimes
    result = []
    for row in rows:
        d = {}
        for k, v in dict(row).items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
            else:
                d[k] = v
        result.append(d)
    return result


def export_to_json(
    db: Session,
    org_id: str,
    org_name: str,
    product_id: str | None,
    product_name: str | None,
    period_start: str | None,
    period_end: str | None,
) -> str:
    """Exporta todos os dados em JSON. Retorna caminho do arquivo."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(EXPORT_DIR, f"{file_id}.json")

    export_data = {
        "export_info": {
            "org_name": org_name,
            "product_name": product_name,
            "exported_at": datetime.utcnow().isoformat(),
            "period": {"start": period_start, "end": period_end},
            "memora_version": "0.2.0",
        },
    }

    for table_name in EXPORTABLE_TABLES:
        try:
            data = _fetch_table_data(db, table_name, org_id, product_id, period_start, period_end)
            export_data[table_name] = data
        except Exception as e:
            logger.warning("Falha ao exportar tabela %s: %s", table_name, e)
            export_data[table_name] = []

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    return file_path


def export_to_csv_zip(
    db: Session,
    org_id: str,
    product_id: str | None,
    period_start: str | None,
    period_end: str | None,
) -> str:
    """Exporta dados em CSV ZIP. Retorna caminho do arquivo."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(EXPORT_DIR, f"{file_id}.zip")

    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for table_name in EXPORTABLE_TABLES:
            try:
                data = _fetch_table_data(db, table_name, org_id, product_id, period_start, period_end)
                if not data:
                    continue

                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                zf.writestr(f"{table_name}.csv", buf.getvalue())
            except Exception as e:
                logger.warning("Falha ao exportar CSV %s: %s", table_name, e)

    return file_path


def run_export(
    db: Session,
    export_id: str,
    org_id: str,
    org_name: str,
    product_id: str | None,
    product_name: str | None,
    format: str,
    period_start: str | None,
    period_end: str | None,
) -> None:
    """Executa exportacao em background e atualiza status."""
    try:
        db.execute(
            text("UPDATE data_exports SET status = 'processing' WHERE id = :id"),
            {"id": export_id},
        )
        db.commit()

        if format == "json":
            file_path = export_to_json(db, org_id, org_name, product_id, product_name, period_start, period_end)
        else:
            file_path = export_to_csv_zip(db, org_id, product_id, period_start, period_end)

        file_size = os.path.getsize(file_path)
        expires_at = datetime.utcnow() + timedelta(days=EXPORT_EXPIRY_DAYS)

        db.execute(
            text("""
                UPDATE data_exports
                SET status = 'ready', file_path = :fp, file_size_bytes = :size,
                    expires_at = :expires, completed_at = NOW()
                WHERE id = :id
            """),
            {"id": export_id, "fp": file_path, "size": file_size, "expires": expires_at},
        )
        db.commit()

        # Send email notification
        try:
            from app.core.email_client import send_to_org_admins
            send_to_org_admins(
                db, org_id,
                subject=f"Memora — Exportacao de dados pronta",
                body_html=f"<p>Sua exportacao de dados ({format.upper()}) esta pronta para download.</p>"
                          f"<p>O arquivo ficara disponivel por {EXPORT_EXPIRY_DAYS} dias.</p>",
                category="export",
            )
        except Exception:
            pass

        logger.info("Exportacao %s concluida: %s (%d bytes)", export_id, file_path, file_size)

    except Exception as e:
        logger.error("Exportacao %s falhou: %s", export_id, e)
        try:
            db.execute(
                text("UPDATE data_exports SET status = 'failed', completed_at = NOW() WHERE id = :id"),
                {"id": export_id},
            )
            db.commit()
        except Exception:
            pass


def cleanup_expired_exports(db: Session) -> int:
    """Remove arquivos expirados. Retorna quantidade removida."""
    rows = db.execute(
        text("""
            SELECT id, file_path FROM data_exports
            WHERE status = 'ready' AND expires_at < NOW()
        """),
    ).fetchall()

    count = 0
    for row in rows:
        if row.file_path and os.path.exists(row.file_path):
            try:
                os.remove(row.file_path)
            except Exception:
                pass
        count += 1

    if count > 0:
        db.execute(
            text("UPDATE data_exports SET status = 'expired', file_path = NULL WHERE status = 'ready' AND expires_at < NOW()"),
        )
        db.commit()

    return count
