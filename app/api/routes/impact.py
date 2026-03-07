"""Rotas de analise de impacto de mudancas."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_role
from app.models.user import User

router = APIRouter(prefix="/impact")


# ---------- Schemas ----------

class AnalyzeRequest(BaseModel):
    change_description: str
    repo_name: str
    affected_files: list[str] | None = None


# ---------- Helpers ----------

def _run_analysis(db: Session, analysis_id: str, org_id: str):
    from app.core.impact_analyzer import ImpactAnalyzer
    try:
        analyzer = ImpactAnalyzer(db, org_id)
        analyzer.analyze(analysis_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Falha na analise de impacto: %s", e)


# ---------- Endpoints ----------

@router.post("/analyze")
def start_analysis(
    body: AnalyzeRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Start an impact analysis in background."""
    import json

    analysis_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO impact_analyses
                (id, org_id, repo_name, requested_by, change_description, affected_files, status)
            VALUES (:id, :org_id, :repo, :user_id, :desc, :files, 'pending')
        """),
        {
            "id": analysis_id,
            "org_id": user.org_id,
            "repo": body.repo_name,
            "user_id": user.id,
            "desc": body.change_description,
            "files": json.dumps(body.affected_files) if body.affected_files else None,
        },
    )
    db.commit()

    bg.add_task(_run_analysis, db, analysis_id, user.org_id)

    return {"analysis_id": analysis_id, "status": "analyzing"}


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Get analysis detail with findings."""
    analysis = db.execute(
        text("SELECT * FROM impact_analyses WHERE id = :id AND org_id = :org_id"),
        {"id": analysis_id, "org_id": user.org_id},
    ).mappings().first()

    if not analysis:
        raise HTTPException(404, "Analise nao encontrada")

    findings = db.execute(
        text("""
            SELECT * FROM impact_findings
            WHERE analysis_id = :id AND org_id = :org_id
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END
        """),
        {"id": analysis_id, "org_id": user.org_id},
    ).mappings().all()

    return {
        **dict(analysis),
        "findings": [dict(f) for f in findings],
    }


@router.get("/{analysis_id}/findings")
def get_findings(
    analysis_id: str,
    severity: str | None = None,
    finding_type: str | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """List findings with optional filters."""
    from app.core.query_builder import build_where_clause

    conditions = ["analysis_id = :id", "org_id = :org_id"]
    params: dict = {"id": analysis_id, "org_id": user.org_id}

    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity
    if finding_type:
        conditions.append("finding_type = :ftype")
        params["ftype"] = finding_type

    where = build_where_clause("impact_findings", conditions)
    rows = db.execute(
        text(f"SELECT * FROM impact_findings WHERE {where} ORDER BY created_at"),
        params,
    ).mappings().all()

    return {"findings": [dict(r) for r in rows]}


@router.get("/history/list")
def list_analyses(
    repo_name: str | None = None,
    page: int = 1,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """List user's past analyses."""
    conditions = ["org_id = :org_id", "requested_by = :user_id"]
    params: dict = {"org_id": user.org_id, "user_id": user.id}

    if repo_name:
        conditions.append("repo_name = :repo")
        params["repo"] = repo_name

    where = " AND ".join(conditions)
    limit = 20
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    rows = db.execute(
        text(f"""
            SELECT id, repo_name, change_description, risk_level, status, created_at
            FROM impact_analyses
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).mappings().all()

    total = db.execute(
        text(f"SELECT COUNT(*) as cnt FROM impact_analyses WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    ).mappings().first()

    return {
        "analyses": [dict(r) for r in rows],
        "total": total["cnt"] if total else 0,
        "page": page,
    }


@router.get("/{analysis_id}/report/pdf")
def download_impact_pdf(
    analysis_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Download impact analysis report as PDF."""
    analysis = db.execute(
        text("SELECT * FROM impact_analyses WHERE id = :id AND org_id = :org_id"),
        {"id": analysis_id, "org_id": user.org_id},
    ).mappings().first()
    if not analysis:
        raise HTTPException(404, "Analise nao encontrada")

    findings = db.execute(
        text("SELECT * FROM impact_findings WHERE analysis_id = :id ORDER BY severity"),
        {"id": analysis_id},
    ).mappings().all()

    from app.core.pdf_generator import PDFGenerator

    pdf = PDFGenerator().generate_impact_report(dict(analysis), [dict(f) for f in findings])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="impact-{analysis_id}.pdf"'},
    )
