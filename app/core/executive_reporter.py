"""Gera snapshots executivos com metricas consolidadas de todos os modulos."""
import json
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

EXECUTIVE_PROMPT = """Voce e um CTO explicando a semana tecnologica para o dono da empresa.
Use linguagem simples, sem jargao tecnico.
Seja direto — o que foi bem, o que precisa de atencao e o que fazer.

DADOS DO PERIODO ({period_start} a {period_end}):
{metrics}

Gere em JSON valido (sem markdown):
{{
  "health_score": 0-100,
  "summary": "3-4 frases resumindo o periodo em linguagem de negocio",
  "highlights": [
    {{"type": "positive|negative|neutral", "text": "..."}}
  ],
  "risks": [
    {{"severity": "low|medium|high", "description": "...", "recommendation": "..."}}
  ],
  "recommendations": [
    {{"priority": 1, "action": "...", "reason": "..."}}
  ]
}}

Exemplos de linguagem correta:
- "O sistema ficou estavel esta semana — nenhuma interrupcao para os usuarios"
- "Foram encontrados 3 problemas de seguranca no codigo antes de chegarem em producao"
- "O time publicou 12 melhorias no sistema — qualidade acima da media"
"""


class ExecutiveReporter:
    def __init__(self, db: Session, org_id: str):
        self.db = db
        self.org_id = org_id

    def generate_snapshot(self, period: str = "week") -> dict:
        """Generate an executive snapshot for the given period."""
        now = datetime.utcnow()
        if period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        else:
            start = now - timedelta(days=7)

        metrics = self._collect_metrics(start, now)
        metrics_text = json.dumps(metrics, ensure_ascii=False, indent=2)

        try:
            result = llm_router.complete(
                db=self.db,
                system_prompt="Voce e um CTO gerando um relatorio executivo.",
                user_message=EXECUTIVE_PROMPT.format(
                    period_start=start.strftime("%d/%m/%Y"),
                    period_end=now.strftime("%d/%m/%Y"),
                    metrics=metrics_text,
                ),
                org_id=self.org_id,
                max_tokens=2048,
            )
            parsed = json.loads(self._clean_json(result["content"]))
        except Exception as e:
            logger.error("Falha ao gerar snapshot executivo: %s", e)
            parsed = self._fallback_snapshot(metrics)

        health_score = parsed.get("health_score", 80)
        if not isinstance(health_score, int):
            health_score = 80
        health_score = max(0, min(100, health_score))

        snapshot_id = str(uuid.uuid4())
        self.db.execute(
            text("""
                INSERT INTO executive_snapshots
                    (id, org_id, generated_at, period_start, period_end,
                     health_score, summary, highlights, risks, recommendations, metrics)
                VALUES (:id, :org_id, now(), :start, :end,
                        :score, :summary, :highlights, :risks, :recs, :metrics)
            """),
            {
                "id": snapshot_id,
                "org_id": self.org_id,
                "start": start,
                "end": now,
                "score": health_score,
                "summary": str(parsed.get("summary", ""))[:2000],
                "highlights": json.dumps(parsed.get("highlights", []), ensure_ascii=False),
                "risks": json.dumps(parsed.get("risks", []), ensure_ascii=False),
                "recs": json.dumps(parsed.get("recommendations", []), ensure_ascii=False),
                "metrics": json.dumps(metrics, ensure_ascii=False),
            },
        )
        self.db.commit()

        return {
            "id": snapshot_id,
            "health_score": health_score,
            "summary": parsed.get("summary", ""),
            "highlights": parsed.get("highlights", []),
            "risks": parsed.get("risks", []),
            "recommendations": parsed.get("recommendations", []),
            "metrics": metrics,
            "period_start": start.isoformat(),
            "period_end": now.isoformat(),
        }

    def _collect_metrics(self, start: datetime, end: datetime) -> dict:
        """Collect metrics from all modules."""
        metrics: dict = {}

        # Monitor — Alerts
        try:
            alert_stats = self.db.execute(
                text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE severity = 'critical') as critical,
                        COUNT(*) FILTER (WHERE severity = 'high') as high,
                        COUNT(*) FILTER (WHERE status = 'open') as open_alerts,
                        COUNT(*) FILTER (WHERE status = 'resolved') as resolved
                    FROM error_alerts
                    WHERE org_id = :org_id AND created_at >= :start AND created_at <= :end
                """),
                {"org_id": self.org_id, "start": start, "end": end},
            ).mappings().first()
            metrics["alertas"] = dict(alert_stats) if alert_stats else {}
        except Exception:
            metrics["alertas"] = {}

        # Incidents
        try:
            inc_stats = self.db.execute(
                text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'resolved') as resolved,
                        COUNT(*) FILTER (WHERE status IN ('open', 'investigating')) as active,
                        AVG(EXTRACT(EPOCH FROM (resolved_at - declared_at)) / 3600)
                            FILTER (WHERE status = 'resolved') as avg_hours
                    FROM incidents
                    WHERE org_id = :org_id AND declared_at >= :start AND declared_at <= :end
                """),
                {"org_id": self.org_id, "start": start, "end": end},
            ).mappings().first()
            metrics["incidentes"] = {
                "total": inc_stats["total"] if inc_stats else 0,
                "resolvidos": inc_stats["resolved"] if inc_stats else 0,
                "ativos": inc_stats["active"] if inc_stats else 0,
                "tempo_medio_horas": round(float(inc_stats["avg_hours"]), 1) if inc_stats and inc_stats["avg_hours"] else None,
            }
        except Exception:
            metrics["incidentes"] = {}

        # Repos
        try:
            repo_count = self.db.execute(
                text("""
                    SELECT COUNT(DISTINCT repo_name) as cnt
                    FROM code_chunks WHERE org_id = :org_id
                """),
                {"org_id": self.org_id},
            ).mappings().first()
            metrics["repositorios"] = {"indexados": repo_count["cnt"] if repo_count else 0}
        except Exception:
            metrics["repositorios"] = {}

        # Code generations
        try:
            gen_count = self.db.execute(
                text("""
                    SELECT COUNT(*) as cnt FROM code_generations
                    WHERE org_id = :org_id AND created_at >= :start AND created_at <= :end
                """),
                {"org_id": self.org_id, "start": start, "end": end},
            ).mappings().first()
            total_gens = gen_count["cnt"] if gen_count else 0
            metrics["geracoes_codigo"] = {
                "total": total_gens,
                "economia_estimada_horas": round(total_gens * 0.5, 1),
            }
        except Exception:
            metrics["geracoes_codigo"] = {}

        # Monitored projects
        try:
            proj_stats = self.db.execute(
                text("""
                    SELECT mp.name,
                        COUNT(ea.id) FILTER (WHERE ea.status = 'open' AND ea.severity IN ('high', 'critical')) as critical_open,
                        COUNT(ea.id) FILTER (WHERE ea.status = 'open') as total_open,
                        MAX(ea.created_at) as last_alert
                    FROM monitored_projects mp
                    LEFT JOIN error_alerts ea ON ea.project_id = mp.id
                        AND ea.created_at >= :start
                    WHERE mp.org_id = :org_id AND mp.is_active = true
                    GROUP BY mp.name
                """),
                {"org_id": self.org_id, "start": start},
            ).mappings().all()
            metrics["projetos"] = [dict(p) for p in proj_stats]
        except Exception:
            metrics["projetos"] = []

        return metrics

    def _fallback_snapshot(self, metrics: dict) -> dict:
        """Generate a basic snapshot without LLM."""
        alerts = metrics.get("alertas", {})
        incidents = metrics.get("incidentes", {})
        score = 100
        if alerts.get("critical", 0) > 0:
            score -= min(30, alerts["critical"] * 15)
        if alerts.get("high", 0) > 0:
            score -= min(20, alerts["high"] * 5)
        if incidents.get("ativos", 0) > 0:
            score -= min(20, incidents["ativos"] * 10)
        score = max(0, score)

        return {
            "health_score": score,
            "summary": "Relatorio gerado automaticamente sem analise de IA.",
            "highlights": [],
            "risks": [],
            "recommendations": [],
        }

    def _clean_json(self, raw: str) -> str:
        t = raw.strip()
        if t.startswith("```"):
            lines = t.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            t = "\n".join(lines)
        return t


def get_realtime_metrics(db: Session, org_id: str) -> dict:
    """Get real-time metrics (not saved)."""
    try:
        alerts_open = db.execute(
            text("SELECT COUNT(*) as cnt FROM error_alerts WHERE org_id = :org_id AND status = 'open'"),
            {"org_id": org_id},
        ).mappings().first()

        incidents_open = db.execute(
            text("SELECT COUNT(*) as cnt FROM incidents WHERE org_id = :org_id AND status IN ('open', 'investigating')"),
            {"org_id": org_id},
        ).mappings().first()

        repos = db.execute(
            text("SELECT COUNT(DISTINCT repo_name) as cnt FROM code_chunks WHERE org_id = :org_id"),
            {"org_id": org_id},
        ).mappings().first()

        projects = db.execute(
            text("SELECT COUNT(*) as cnt FROM monitored_projects WHERE org_id = :org_id AND is_active = true"),
            {"org_id": org_id},
        ).mappings().first()

        return {
            "systems_monitored": projects["cnt"] if projects else 0,
            "alerts_open": alerts_open["cnt"] if alerts_open else 0,
            "incidents_open": incidents_open["cnt"] if incidents_open else 0,
            "repos_indexed": repos["cnt"] if repos else 0,
        }
    except Exception:
        return {"systems_monitored": 0, "alerts_open": 0, "incidents_open": 0, "repos_indexed": 0}
