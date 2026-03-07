"""MCP tool: analisa o impacto de uma mudanca planejada."""
import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder
from app.integrations import llm_router

logger = logging.getLogger(__name__)


def analyze_change_impact(
    db: Session,
    org_id: str,
    change_description: str,
    repo_name: str,
    affected_files: list[str] | None = None,
) -> str:
    """Analyze impact of a planned change and return formatted report."""
    # Quick context collection
    deps = _find_deps(db, org_id, repo_name, change_description)
    rules = _find_rules(db, org_id, change_description)
    decisions = _find_decisions(db, org_id, change_description)

    prompt = f"""Voce e um arquiteto avaliando o risco de uma mudanca.

MUDANCA: {change_description}
ARQUIVOS: {', '.join(affected_files) if affected_files else 'Nao especificados'}

DEPENDENCIAS:
{deps}

REGRAS DE NEGOCIO:
{rules}

DECISOES ARQUITETURAIS:
{decisions}

Gere um relatorio conciso em portugues:
1. Nivel de risco: low | medium | high | critical
2. Resumo em 2 frases
3. Findings relevantes (maximo 5)
4. Recomendacoes

Responda em JSON: {{"risk_level": "...", "summary": "...", "findings": [...], "recommendations": [...]}}"""

    try:
        result = llm_router.complete(
            db=db,
            system_prompt="Voce e um arquiteto senior avaliando riscos de mudancas.",
            user_message=prompt,
            org_id=org_id,
            max_tokens=2048,
        )
        report = json.loads(_clean(result["content"]))
    except Exception as e:
        return f"Erro na analise de impacto: {str(e)[:200]}"

    # Format output
    lines = [f"Analise de impacto — Risco: {report.get('risk_level', 'N/A').upper()}", ""]
    lines.append(report.get("summary", ""))
    lines.append("")

    for f in report.get("findings", []):
        ftype = f.get("type", "dependency")
        icon = {"dependency": "dep", "business_rule": "regra", "pattern_break": "padrao", "similar_change": "hist"}.get(ftype, ftype)
        lines.append(f"[{icon}] {f.get('title', '')}: {f.get('description', '')}")
        if f.get("recommendation"):
            lines.append(f"  Recomendacao: {f['recommendation']}")
        lines.append("")

    recs = report.get("recommendations", [])
    if recs:
        lines.append("Proximos passos:")
        for i, r in enumerate(recs, 1):
            lines.append(f"  {i}. {r}")

    return "\n".join(lines)


def _find_deps(db: Session, org_id: str, repo_name: str, desc: str) -> str:
    try:
        rows = db.execute(
            text("""
                SELECT file_path, chunk_name FROM code_chunks
                WHERE org_id = :org_id AND repo_name = :repo AND content ILIKE :pat
                LIMIT 10
            """),
            {"org_id": org_id, "repo": repo_name, "pat": f"%{desc[:50]}%"},
        ).mappings().all()
        return "\n".join(f"- {r['file_path']}:{r['chunk_name']}" for r in rows) or "Nenhuma"
    except Exception:
        return "Nenhuma"


def _find_rules(db: Session, org_id: str, desc: str) -> str:
    try:
        embedder = Embedder()
        emb = embedder.embed_text(desc)
        rows = db.execute(
            text("""
                SELECT title, plain_english,
                       1 - (embedding <=> CAST(:emb AS vector)) as score
                FROM business_rules WHERE org_id = :org_id
                ORDER BY embedding <=> CAST(:emb AS vector) LIMIT 3
            """),
            {"org_id": org_id, "emb": str(emb)},
        ).mappings().all()
        return "\n".join(
            f"- {r['title']}: {r['plain_english']}" for r in rows if r["score"] > 0.5
        ) or "Nenhuma"
    except Exception:
        return "Nenhuma"


def _find_decisions(db: Session, org_id: str, desc: str) -> str:
    try:
        embedder = Embedder()
        emb = embedder.embed_text(desc)
        rows = db.execute(
            text("""
                SELECT title, summary,
                       1 - (embedding <=> CAST(:emb AS vector)) as score
                FROM knowledge_entries
                WHERE org_id = :org_id AND source_type IN ('adr', 'pr')
                ORDER BY embedding <=> CAST(:emb AS vector) LIMIT 3
            """),
            {"org_id": org_id, "emb": str(emb)},
        ).mappings().all()
        return "\n".join(
            f"- {r['title']}: {(r.get('summary') or '')[:150]}" for r in rows if r["score"] > 0.5
        ) or "Nenhuma"
    except Exception:
        return "Nenhuma"


def _clean(raw: str) -> str:
    t = raw.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        t = "\n".join(lines)
    return t
