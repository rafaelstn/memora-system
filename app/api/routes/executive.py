"""Rotas do painel executivo."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session, require_role
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/executive")


@router.get("/snapshot/latest")
def get_latest_snapshot(
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
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
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Generate a new executive snapshot on-demand."""
    from app.core.executive_reporter import ExecutiveReporter

    reporter = ExecutiveReporter(db, user.org_id)
    return reporter.generate_snapshot(period)


@router.get("/snapshot/history")
def snapshot_history(
    page: int = 1,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
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
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Get real-time metrics."""
    from app.core.executive_reporter import get_realtime_metrics
    return get_realtime_metrics(db, user.org_id)


@router.get("/snapshot/{snapshot_id}/pdf")
def download_executive_pdf(
    snapshot_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
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


# ── Weekly History ─────────────────────────────────────────


@router.get("/history")
def get_executive_history(
    period: str = Query("4w", pattern="^(4w|3m|6m)$"),
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Retorna snapshots semanais historicos filtrados por periodo."""
    from app.core.executive_weekly import get_history
    return get_history(db, user.org_id, product.id, period)


@router.get("/history/csv")
def get_executive_history_csv(
    period: str = Query("4w", pattern="^(4w|3m|6m)$"),
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Exporta snapshots semanais em CSV."""
    from app.core.executive_weekly import get_history_csv
    csv_content = get_history_csv(db, user.org_id, product.id, period)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="executive-history.csv"'},
    )


@router.post("/history/generate-now")
def generate_weekly_snapshot_now(
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Gera snapshot semanal manualmente (admin only)."""
    from app.core.executive_weekly import save_weekly_snapshot
    return save_weekly_snapshot(db, user.org_id, product.id)
