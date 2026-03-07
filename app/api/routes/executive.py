"""Rotas do painel executivo."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_role
from app.models.user import User

router = APIRouter(prefix="/executive")


@router.get("/snapshot/latest")
def get_latest_snapshot(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Get the most recent executive snapshot."""
    row = db.execute(
        text("""
            SELECT * FROM executive_snapshots
            WHERE org_id = :org_id
            ORDER BY generated_at DESC
            LIMIT 1
        """),
        {"org_id": user.org_id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Nenhum snapshot encontrado")

    return dict(row)


@router.get("/snapshot/generate")
def generate_snapshot(
    period: str = "week",
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Generate a new executive snapshot on-demand."""
    from app.core.executive_reporter import ExecutiveReporter

    reporter = ExecutiveReporter(db, user.org_id)
    return reporter.generate_snapshot(period)


@router.get("/snapshot/history")
def snapshot_history(
    page: int = 1,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """List past snapshots."""
    limit = 20
    offset = (page - 1) * limit
    rows = db.execute(
        text("""
            SELECT id, generated_at, period_start, period_end, health_score, summary
            FROM executive_snapshots
            WHERE org_id = :org_id
            ORDER BY generated_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"org_id": user.org_id, "limit": limit, "offset": offset},
    ).mappings().all()

    total = db.execute(
        text("SELECT COUNT(*) as cnt FROM executive_snapshots WHERE org_id = :org_id"),
        {"org_id": user.org_id},
    ).mappings().first()

    return {
        "snapshots": [dict(r) for r in rows],
        "total": total["cnt"] if total else 0,
        "page": page,
    }


@router.get("/metrics")
def realtime_metrics(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Get real-time metrics."""
    from app.core.executive_reporter import get_realtime_metrics
    return get_realtime_metrics(db, user.org_id)


@router.get("/snapshot/{snapshot_id}/pdf")
def download_executive_pdf(
    snapshot_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Download executive snapshot as PDF."""
    row = db.execute(
        text("SELECT * FROM executive_snapshots WHERE id = :id AND org_id = :org_id"),
        {"id": snapshot_id, "org_id": user.org_id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Snapshot nao encontrado")

    from app.core.pdf_generator import PDFGenerator

    pdf = PDFGenerator().generate_executive_report(dict(row))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="executive-{snapshot_id}.pdf"'},
    )
