"""Analisa incidentes e gera hipoteses sobre a causa raiz usando IA."""
import json
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder
from app.integrations import llm_router

logger = logging.getLogger(__name__)

HYPOTHESIS_PROMPT = """Voce e um engenheiro senior investigando um incidente em producao.
Analise o contexto abaixo e gere hipoteses sobre a causa raiz.

ERRO DETECTADO:
{explanation}

STACK TRACE:
{stack_trace}

LOGS RECENTES (ultimas 2h):
{recent_logs}

ULTIMAS MUDANCAS NO CODIGO (ultimas 24h):
{recent_prs}

INCIDENTES SIMILARES NO PASSADO:
{similar_incidents}

Gere 3 hipoteses sobre a causa raiz, ordenadas por probabilidade.
Para cada hipotese:
1. Descreva a causa em portugues simples
2. Explique o raciocinio
3. Diga o que verificar para confirmar ou descartar
4. Estime a confianca (0.0 a 1.0)

Responda SOMENTE com JSON valido, sem markdown:
[{{"hypothesis": "...", "reasoning": "...", "what_to_check": "...", "confidence": 0.8}}]"""


class IncidentAnalyzer:
    def __init__(self, db: Session, org_id: str):
        self.db = db
        self.org_id = org_id

    def generate_hypotheses(self, incident_id: str):
        """Collect context and generate AI hypotheses for an incident."""
        incident = self.db.execute(
            text("SELECT * FROM incidents WHERE id = :id AND org_id = :org_id"),
            {"id": incident_id, "org_id": self.org_id},
        ).mappings().first()

        if not incident:
            logger.warning("Incidente %s nao encontrado", incident_id)
            return

        # Collect context
        explanation = ""
        stack_trace = "Nao disponivel"
        if incident["alert_id"]:
            alert = self.db.execute(
                text("""
                    SELECT ea.*, le.stack_trace, le.message as log_message
                    FROM error_alerts ea
                    LEFT JOIN log_entries le ON le.id = ea.log_entry_id
                    WHERE ea.id = :id
                """),
                {"id": incident["alert_id"]},
            ).mappings().first()
            if alert:
                explanation = alert.get("explanation", "")
                stack_trace = alert.get("stack_trace") or "Nao disponivel"

        if not explanation:
            explanation = f"{incident['title']}: {incident.get('description') or 'Sem descricao adicional'}"

        # Recent logs (last 2h)
        cutoff = datetime.utcnow() - timedelta(hours=2)
        recent = self.db.execute(
            text("""
                SELECT level, message, source, received_at
                FROM log_entries
                WHERE project_id = :pid AND received_at >= :cutoff
                ORDER BY received_at DESC LIMIT 50
            """),
            {"pid": incident["project_id"], "cutoff": cutoff},
        ).mappings().all()
        recent_logs = "\n".join(
            f"[{r['level']}] {r['message'][:200]}" for r in recent
        ) or "Nenhum log recente encontrado"

        # Recent PRs from knowledge_entries (last 24h)
        pr_cutoff = datetime.utcnow() - timedelta(hours=24)
        prs = self.db.execute(
            text("""
                SELECT title, summary
                FROM knowledge_entries
                WHERE org_id = :org_id AND source_type = 'pr'
                  AND created_at >= :cutoff
                ORDER BY created_at DESC LIMIT 10
            """),
            {"org_id": self.org_id, "cutoff": pr_cutoff},
        ).mappings().all()
        recent_prs = "\n".join(
            f"- {p['title']}: {(p.get('summary') or '')[:200]}" for p in prs
        ) or "Nenhuma mudanca recente encontrada"

        # Similar past incidents
        past = self.db.execute(
            text("""
                SELECT title, resolution_summary, severity
                FROM incidents
                WHERE org_id = :org_id AND status = 'resolved' AND id != :id
                ORDER BY created_at DESC LIMIT 5
            """),
            {"org_id": self.org_id, "id": incident_id},
        ).mappings().all()
        similar_incidents = "\n".join(
            f"- {p['title']} ({p['severity']}): {(p.get('resolution_summary') or 'sem resolucao')[:200]}"
            for p in past
        ) or "Nenhum incidente similar encontrado"

        # Generate hypotheses via LLM
        prompt = HYPOTHESIS_PROMPT.format(
            explanation=explanation,
            stack_trace=stack_trace,
            recent_logs=recent_logs,
            recent_prs=recent_prs,
            similar_incidents=similar_incidents,
        )

        try:
            result = llm_router.complete(
                db=self.db,
                system_prompt="Voce e um engenheiro senior de plantao analisando incidentes.",
                user_message=prompt,
                org_id=self.org_id,
                max_tokens=2048,
            )
            hypotheses = self._parse_hypotheses(result["content"])
        except Exception as e:
            logger.error("Falha ao gerar hipoteses para incidente %s: %s", incident_id, e)
            hypotheses = [{
                "hypothesis": "Nao foi possivel gerar hipoteses automaticamente. Verifique os logs e o stack trace manualmente.",
                "reasoning": f"Erro na analise: {str(e)[:200]}",
                "confidence": 0.3,
            }]

        # Save hypotheses
        for h in hypotheses:
            h_id = str(uuid.uuid4())
            confidence = h.get("confidence", 0.5)
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            confidence = max(0.0, min(1.0, float(confidence)))

            self.db.execute(
                text("""
                    INSERT INTO incident_hypotheses
                        (id, incident_id, org_id, hypothesis, reasoning, confidence, status)
                    VALUES (:id, :incident_id, :org_id, :hypothesis, :reasoning, :confidence, 'open')
                """),
                {
                    "id": h_id,
                    "incident_id": incident_id,
                    "org_id": self.org_id,
                    "hypothesis": str(h.get("hypothesis", ""))[:2000],
                    "reasoning": str(h.get("reasoning", ""))[:2000],
                    "confidence": confidence,
                },
            )

            # Timeline event for each hypothesis
            self.db.execute(
                text("""
                    INSERT INTO incident_timeline
                        (id, incident_id, org_id, event_type, content, is_ai_generated)
                    VALUES (:id, :incident_id, :org_id, 'hypothesis', :content, true)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "incident_id": incident_id,
                    "org_id": self.org_id,
                    "content": f"Hipotese (confianca {confidence:.0%}): {str(h.get('hypothesis', ''))[:500]}",
                },
            )

        # Summary timeline event
        self.db.execute(
            text("""
                INSERT INTO incident_timeline
                    (id, incident_id, org_id, event_type, content, is_ai_generated)
                VALUES (:id, :incident_id, :org_id, 'hypothesis', :content, true)
            """),
            {
                "id": str(uuid.uuid4()),
                "incident_id": incident_id,
                "org_id": self.org_id,
                "content": f"IA gerou {len(hypotheses)} hipotese(s) sobre a causa raiz",
            },
        )

        self.db.commit()
        logger.info("Hipoteses geradas para incidente %s: %d", incident_id, len(hypotheses))

    def find_similar(self, incident_id: str, limit: int = 5) -> list[dict]:
        """Find similar resolved incidents using text embedding similarity."""
        incident = self.db.execute(
            text("SELECT title, description FROM incidents WHERE id = :id AND org_id = :org_id"),
            {"id": incident_id, "org_id": self.org_id},
        ).mappings().first()

        if not incident:
            return []

        query_text = f"{incident['title']} {incident.get('description') or ''}"

        try:
            embedder = Embedder()
            embedding = embedder.embed_text(query_text)
        except Exception as e:
            logger.error("Falha ao gerar embedding para find_similar: %s", e)
            return []

        # Search resolved incidents by embedding similarity
        similar = self.db.execute(
            text("""
                SELECT i.id, i.title, i.severity, i.resolved_at, i.resolution_summary,
                       mp.name as project_name,
                       1 - (ie.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM incident_embeddings ie
                JOIN incidents i ON i.id = ie.incident_id
                JOIN monitored_projects mp ON mp.id = i.project_id
                WHERE i.org_id = :org_id
                  AND i.status = 'resolved'
                  AND i.id != :current_id
                ORDER BY ie.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            {
                "embedding": str(embedding),
                "org_id": self.org_id,
                "current_id": incident_id,
                "limit": limit,
            },
        ).mappings().all()

        results = []
        for s in similar:
            score = float(s["similarity"]) if s["similarity"] else 0
            if score < 0.3:
                continue
            results.append({
                "id": s["id"],
                "title": s["title"],
                "severity": s["severity"],
                "project_name": s["project_name"],
                "resolved_at": str(s["resolved_at"]) if s["resolved_at"] else None,
                "resolution_summary": (s.get("resolution_summary") or "")[:300],
                "similarity": round(score, 3),
            })

        # Save to incident_similar_incidents
        for r in results:
            self.db.execute(
                text("""
                    INSERT INTO incident_similar_incidents
                        (id, incident_id, similar_incident_id, similarity_score)
                    VALUES (:id, :incident_id, :similar_id, :score)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "incident_id": incident_id,
                    "similar_id": r["id"],
                    "score": r["similarity"],
                },
            )
        if results:
            self.db.commit()

        return results

    def _parse_hypotheses(self, raw: str) -> list[dict]:
        """Parse JSON list of hypotheses from LLM response."""
        text_clean = raw.strip()
        if text_clean.startswith("```"):
            lines = text_clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text_clean = "\n".join(lines)

        try:
            parsed = json.loads(text_clean)
            if isinstance(parsed, list):
                return parsed[:5]
            return [parsed]
        except json.JSONDecodeError:
            return [{
                "hypothesis": raw[:500],
                "reasoning": "Resposta nao estruturada da IA",
                "confidence": 0.4,
            }]
