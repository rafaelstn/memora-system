"""Analisa logs de erro com IA e gera alertas explicativos em portugues."""
import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Voce e um especialista em analise de erros de software.
Analise o erro abaixo e responda em portugues brasileiro.
Seja direto e pratico — quem vai ler e o responsavel tecnico do sistema.

Responda SOMENTE com JSON valido, sem markdown, sem texto extra:
{
  "title": "titulo curto e descritivo do erro",
  "explanation": "o que aconteceu em linguagem simples (2-3 paragrafos)",
  "severity": "low|medium|high|critical",
  "affected_component": "qual parte do sistema foi afetada",
  "suggested_actions": [
    "Primeira coisa a verificar",
    "Segunda acao sugerida",
    "Terceira acao se as anteriores nao resolverem"
  ]
}"""


def _build_user_message(log_entry: dict, recent_logs: list[dict]) -> str:
    parts = [
        f"Nivel: {log_entry['level']}",
        f"Mensagem: {log_entry['message']}",
    ]
    if log_entry.get("source"):
        parts.append(f"Origem: {log_entry['source']}")
    if log_entry.get("stack_trace"):
        parts.append(f"Stack trace:\n{log_entry['stack_trace']}")
    if log_entry.get("metadata"):
        parts.append(f"Metadados: {json.dumps(log_entry['metadata'], ensure_ascii=False)}")

    if recent_logs:
        parts.append("\n--- Ultimos logs do mesmo projeto (contexto) ---")
        for rl in recent_logs[:5]:
            parts.append(f"[{rl['level']}] {rl['message'][:200]}")

    return "\n".join(parts)


def _parse_llm_response(raw: str) -> dict:
    """Parse JSON from LLM response with fallback."""
    # Try to extract JSON from response
    text_clean = raw.strip()
    if text_clean.startswith("```"):
        lines = text_clean.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text_clean = "\n".join(lines)

    try:
        return json.loads(text_clean)
    except json.JSONDecodeError:
        # Fallback: use raw text as explanation
        return {
            "title": "Erro detectado",
            "explanation": raw[:2000],
            "severity": "medium",
            "affected_component": "desconhecido",
            "suggested_actions": ["Verificar logs detalhados do sistema"],
        }


def analyze(db: Session, log_entry_id: str, org_id: str) -> str | None:
    """Analyze a log entry and create an error alert. Returns alert_id or None."""
    entry = db.execute(
        text("SELECT * FROM log_entries WHERE id = :id AND org_id = :org_id"),
        {"id": log_entry_id, "org_id": org_id},
    ).mappings().first()

    if not entry:
        logger.warning("Log entry %s nao encontrada", log_entry_id)
        return None

    # Fetch recent logs for context
    recent = db.execute(
        text("""
            SELECT level, message, source, received_at
            FROM log_entries
            WHERE project_id = :project_id AND id != :id
            ORDER BY received_at DESC LIMIT 5
        """),
        {"project_id": entry["project_id"], "id": log_entry_id},
    ).mappings().all()

    entry_dict = {
        "level": entry["level"],
        "message": entry["message"],
        "source": entry.get("source"),
        "stack_trace": entry.get("stack_trace"),
        "metadata": entry.get("metadata"),
    }
    recent_dicts = [{"level": r["level"], "message": r["message"]} for r in recent]
    user_message = _build_user_message(entry_dict, recent_dicts)

    try:
        result = llm_router.complete(
            db=db,
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            org_id=org_id,
            max_tokens=1024,
        )
        analysis = _parse_llm_response(result["content"])
    except Exception as e:
        logger.error("Falha na analise do log %s: %s", log_entry_id, e)
        analysis = {
            "title": f"Erro: {str(entry['message'])[:100]}",
            "explanation": f"Nao foi possivel analisar automaticamente. Mensagem original: {entry['message']}",
            "severity": "high" if entry["level"] == "critical" else "medium",
            "affected_component": entry.get("source") or "desconhecido",
            "suggested_actions": ["Verificar logs detalhados", "Contatar equipe de desenvolvimento"],
        }

    alert_id = str(uuid.uuid4())
    severity = analysis.get("severity", "medium")
    if severity not in ("low", "medium", "high", "critical"):
        severity = "medium"

    db.execute(
        text("""
            INSERT INTO error_alerts
                (id, project_id, org_id, log_entry_id, title, explanation, severity,
                 affected_component, suggested_actions, status)
            VALUES
                (:id, :project_id, :org_id, :log_entry_id, :title, :explanation, :severity,
                 :affected_component, :suggested_actions, 'open')
        """),
        {
            "id": alert_id,
            "project_id": entry["project_id"],
            "org_id": org_id,
            "log_entry_id": log_entry_id,
            "title": str(analysis.get("title", "Erro detectado"))[:500],
            "explanation": str(analysis.get("explanation", ""))[:5000],
            "severity": severity,
            "affected_component": str(analysis.get("affected_component", ""))[:255],
            "suggested_actions": json.dumps(analysis.get("suggested_actions", []), ensure_ascii=False),
        },
    )

    # Mark log as analyzed
    db.execute(
        text("UPDATE log_entries SET is_analyzed = true WHERE id = :id"),
        {"id": log_entry_id},
    )
    db.commit()

    logger.info("Alerta %s criado para log %s (severity=%s)", alert_id, log_entry_id, severity)
    return alert_id
