"""Gera post-mortem automatico de incidentes usando IA."""
import logging
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

POSTMORTEM_PROMPT = """Voce e um engenheiro senior documentando um post-mortem de incidente.
Com base na timeline abaixo, gere um post-mortem completo em portugues.

TITULO DO INCIDENTE: {title}
SEVERIDADE: {severity}
DECLARADO EM: {declared_at}
RESOLVIDO EM: {resolved_at}

TIMELINE DO INCIDENTE:
{timeline}

HIPOTESES LEVANTADAS:
{hypotheses}

RESOLUCAO:
{resolution_summary}

Estrutura obrigatoria (use markdown):

# Post-mortem — {title}
**Data:** {declared_at}
**Duracao:** {duration}
**Severidade:** {severity}
**Status:** Resolvido

## Resumo executivo
(2-3 frases explicando o que aconteceu e o impacto)

## Linha do tempo
(tabela com horario e evento para cada item da timeline)

## Causa raiz
(causa confirmada em linguagem simples)

## O que foi feito para resolver
(acoes tomadas em ordem cronologica)

## Impacto
(estimativa de tempo de indisponibilidade e sistemas afetados)

## Como evitar no futuro
(3-5 acoes preventivas concretas)

## Licoes aprendidas
(o que o time aprendeu com esse incidente)"""


def generate(db: Session, incident_id: str, org_id: str) -> str | None:
    """Generate a post-mortem for a resolved incident. Returns the markdown or None."""
    incident = db.execute(
        text("SELECT * FROM incidents WHERE id = :id AND org_id = :org_id"),
        {"id": incident_id, "org_id": org_id},
    ).mappings().first()

    if not incident:
        logger.warning("Incidente %s nao encontrado", incident_id)
        return None

    # Collect timeline
    events = db.execute(
        text("""
            SELECT event_type, content, is_ai_generated, created_at, created_by
            FROM incident_timeline
            WHERE incident_id = :id
            ORDER BY created_at ASC
        """),
        {"id": incident_id},
    ).mappings().all()

    timeline_text = "\n".join(
        f"[{e['created_at']}] ({e['event_type']}) {e['content']}"
        for e in events
    ) or "Nenhum evento registrado"

    # Collect hypotheses
    hyps = db.execute(
        text("""
            SELECT hypothesis, reasoning, confidence, status
            FROM incident_hypotheses
            WHERE incident_id = :id
            ORDER BY confidence DESC
        """),
        {"id": incident_id},
    ).mappings().all()

    hypotheses_text = "\n".join(
        f"- [{h['status']}] (confianca {h['confidence']:.0%}) {h['hypothesis']}: {h['reasoning']}"
        for h in hyps
    ) or "Nenhuma hipotese registrada"

    # Calculate duration
    declared = incident["declared_at"]
    resolved = incident.get("resolved_at") or datetime.utcnow()
    # Parse strings to datetime if needed
    if isinstance(declared, str):
        declared = datetime.fromisoformat(declared)
    if isinstance(resolved, str):
        resolved = datetime.fromisoformat(resolved)
    if declared and resolved:
        delta = resolved - declared
        hours = delta.total_seconds() / 3600
        if hours < 1:
            duration = f"{int(delta.total_seconds() / 60)} minutos"
        else:
            duration = f"{hours:.1f} horas"
    else:
        duration = "N/A"

    prompt = POSTMORTEM_PROMPT.format(
        title=incident["title"],
        severity=incident["severity"],
        declared_at=str(incident["declared_at"]),
        resolved_at=str(resolved),
        duration=duration,
        timeline=timeline_text,
        hypotheses=hypotheses_text,
        resolution_summary=incident.get("resolution_summary") or "Nao informado",
    )

    try:
        result = llm_router.complete(
            db=db,
            system_prompt="Voce e um engenheiro senior escrevendo documentacao tecnica.",
            user_message=prompt,
            org_id=org_id,
            max_tokens=4096,
        )
        postmortem_md = result["content"]
    except Exception as e:
        logger.error("Falha ao gerar post-mortem para incidente %s: %s", incident_id, e)
        postmortem_md = f"# Post-mortem — {incident['title']}\n\nNao foi possivel gerar automaticamente.\n\nErro: {str(e)[:200]}"

    # Save
    db.execute(
        text("""
            UPDATE incidents
            SET postmortem = :pm, postmortem_generated_at = now()
            WHERE id = :id
        """),
        {"pm": postmortem_md, "id": incident_id},
    )

    # Timeline event
    db.execute(
        text("""
            INSERT INTO incident_timeline
                (id, incident_id, org_id, event_type, content, is_ai_generated)
            VALUES (:id, :incident_id, :org_id, 'update', 'Post-mortem gerado automaticamente', true)
        """),
        {
            "id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "org_id": org_id,
        },
    )

    db.commit()
    logger.info("Post-mortem gerado para incidente %s", incident_id)
    return postmortem_md
