"""Rotas de exportacao de dados — admin only."""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session, get_session, require_role
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/admin/exports")


class ExportRequest(BaseModel):
    format: str = "json"  # json | csv_zip
    product_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None


@router.post("")
def create_export(
    body: ExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Cria uma nova exportacao de dados (background)."""
    if body.format not in ("json", "csv_zip"):
        raise HTTPException(400, "Formato invalido. Use 'json' ou 'csv_zip'.")

    export_id = str(uuid.uuid4())
    product_id = body.product_id or product.id

    # Buscar nome do produto
    prod_row = db.execute(
        text("SELECT name FROM products WHERE id = :pid"),
        {"pid": product_id},
    ).mappings().first()
    product_name = prod_row["name"] if prod_row else None

    # Buscar nome da org
    org_row = db.execute(
        text("SELECT name FROM organizations WHERE id = :oid"),
        {"oid": user.org_id},
    ).mappings().first()
    org_name = org_row["name"] if org_row else "Organizacao"

    db.execute(
        text("""
            INSERT INTO data_exports (id, org_id, product_id, requested_by, format,
                                      period_start, period_end, status)
            VALUES (:id, :org_id, :product_id, :user_id, :format,
                    :period_start, :period_end, 'pending')
        """),
        {
            "id": export_id,
            "org_id": user.org_id,
            "product_id": product_id,
            "user_id": user.id,
            "format": body.format,
            "period_start": body.period_start,
            "period_end": body.period_end,
        },
    )
    db.commit()

    from app.core.data_exporter import run_export

    background_tasks.add_task(
        run_export,
        db, export_id, user.org_id, org_name,
        product_id, product_name,
        body.format, body.period_start, body.period_end,
    )

    return {"id": export_id, "status": "pending"}


@router.get("")
def list_exports(
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Lista exportacoes da organizacao."""
    rows = db.execute(
        text("""
            SELECT id, product_id, format, period_start, period_end,
                   status, file_size_bytes, expires_at, created_at, completed_at
            FROM data_exports
            WHERE org_id = :org_id
            ORDER BY created_at DESC
            LIMIT 20
        """),
        {"org_id": user.org_id},
    ).mappings().all()

    return [dict(r) for r in rows]


@router.get("/{export_id}/download")
def download_export(
    export_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Download do arquivo exportado."""
    row = db.execute(
        text("""
            SELECT * FROM data_exports
            WHERE id = :id AND org_id = :org_id
        """),
        {"id": export_id, "org_id": user.org_id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Exportacao nao encontrada")

    if row["status"] != "ready":
        raise HTTPException(400, f"Exportacao com status '{row['status']}'. Aguarde a conclusao.")

    if row["expires_at"] and datetime.utcnow() > row["expires_at"].replace(tzinfo=None):
        raise HTTPException(410, "Exportacao expirada. Solicite uma nova.")

    file_path = row["file_path"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(404, "Arquivo nao encontrado")

    ext = "json" if row["format"] == "json" else "zip"
    filename = f"memora-export-{export_id[:8]}.{ext}"
    media_type = "application/json" if ext == "json" else "application/zip"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )
