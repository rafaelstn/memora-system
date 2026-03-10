"""Rotas do analisador de seguranca e DAST."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session, require_role
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/security")


class ScanRequest(BaseModel):
    repo_name: str


class DASTScanRequest(BaseModel):
    target_url: str
    target_env: str = "development"


@router.post("/scan")
def start_security_scan(
    req: ScanRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Start a new security scan for a repo."""
    scan_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO security_scans (id, org_id, product_id, repo_name, requested_by, status)
            VALUES (:id, :org_id, :product_id, :repo, :user_id, 'analyzing')
        """),
        {
            "id": scan_id,
            "org_id": user.org_id,
            "product_id": product.id,
            "repo": req.repo_name,
            "user_id": user.id,
        },
    )
    db.commit()

    from app.core.security_scanner import SecurityScanner
    scanner = SecurityScanner(db, user.org_id)
    bg.add_task(scanner.run, scan_id, req.repo_name)

    return {"scan_id": scan_id, "status": "analyzing"}


@router.get("/scan/{scan_id}")
def get_security_scan(
    scan_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Get scan details."""
    row = db.execute(
        text("""
            SELECT * FROM security_scans
            WHERE id = :id AND product_id = :product_id
        """),
        {"id": scan_id, "product_id": product.id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Scan nao encontrado")
    return dict(row)


@router.get("/scan/{scan_id}/findings")
def get_scan_findings(
    scan_id: str,
    severity: str | None = None,
    scanner: str | None = None,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Get findings for a scan."""
    q = """
        SELECT * FROM security_findings
        WHERE scan_id = :scan_id AND org_id = :org_id
    """
    params: dict = {"scan_id": scan_id, "org_id": user.org_id}
    if severity:
        q += " AND severity = :severity"
        params["severity"] = severity
    if scanner:
        q += " AND scanner = :scanner"
        params["scanner"] = scanner
    q += " ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"

    rows = db.execute(text(q), params).mappings().all()
    return {"findings": [dict(r) for r in rows]}


@router.get("/scan/{scan_id}/dependencies")
def get_dependency_alerts(
    scan_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Get dependency alerts for a scan."""
    rows = db.execute(
        text("""
            SELECT * FROM dependency_alerts
            WHERE scan_id = :scan_id AND org_id = :org_id
            ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
        """),
        {"scan_id": scan_id, "org_id": user.org_id},
    ).mappings().all()
    return {"alerts": [dict(r) for r in rows]}


@router.get("/scans")
def list_security_scans(
    repo_name: str | None = None,
    page: int = 1,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """List past security scans."""
    limit = 20
    offset = (page - 1) * limit
    q = "SELECT * FROM security_scans WHERE product_id = :product_id"
    params: dict = {"product_id": product.id, "limit": limit, "offset": offset}
    if repo_name:
        q += " AND repo_name = :repo"
        params["repo"] = repo_name
    q += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    rows = db.execute(text(q), params).mappings().all()

    count_q = "SELECT COUNT(*) as cnt FROM security_scans WHERE product_id = :product_id"
    count_params: dict = {"product_id": product.id}
    if repo_name:
        count_q += " AND repo_name = :repo"
        count_params["repo"] = repo_name
    total = db.execute(text(count_q), count_params).mappings().first()

    return {
        "scans": [dict(r) for r in rows],
        "total": total["cnt"] if total else 0,
        "page": page,
    }


@router.get("/stats")
def security_stats(
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Get aggregated security stats."""
    latest = db.execute(
        text("""
            SELECT repo_name, security_score, total_findings, critical_count,
                   high_count, created_at
            FROM security_scans
            WHERE product_id = :product_id AND status = 'completed'
            ORDER BY created_at DESC
            LIMIT 10
        """),
        {"product_id": product.id},
    ).mappings().all()

    avg_score = None
    total_critical = 0
    if latest:
        scores = [r["security_score"] for r in latest if r["security_score"] is not None]
        avg_score = round(sum(scores) / len(scores)) if scores else None
        total_critical = sum(r["critical_count"] or 0 for r in latest)

    return {
        "recent_scans": [dict(r) for r in latest],
        "avg_score": avg_score,
        "total_critical_findings": total_critical,
    }


# ────────────────────── DAST Scanner ──────────────────────

@router.post("/dast/scan")
def start_dast_scan(
    req: DASTScanRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Start a DAST scan (admin only)."""
    if req.target_env not in ("development", "staging"):
        raise HTTPException(400, "Ambiente deve ser 'development' ou 'staging'.")

    from app.core.dast_scanner import validate_target_url, validate_target_scope
    error = validate_target_url(req.target_url)
    if error:
        raise HTTPException(403, error)

    scope_error = validate_target_scope(req.target_url, db, user.org_id)
    if scope_error:
        raise HTTPException(403, scope_error)

    scan_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO dast_scans
                (id, org_id, product_id, requested_by, target_url, target_env, status, probes_total)
            VALUES (:id, :org_id, :product_id, :user_id, :url, :env, 'running', 10)
        """),
        {
            "id": scan_id,
            "org_id": user.org_id,
            "product_id": product.id,
            "user_id": user.id,
            "url": req.target_url,
            "env": req.target_env,
        },
    )
    db.commit()

    from app.core.dast_scanner import DASTScanner
    scanner = DASTScanner(db, user.org_id)
    bg.add_task(scanner.run, scan_id, req.target_url)

    return {"scan_id": scan_id, "status": "running"}


@router.get("/dast/scan/{scan_id}")
def get_dast_scan(
    scan_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Get DAST scan progress/result."""
    row = db.execute(
        text("SELECT * FROM dast_scans WHERE id = :id AND org_id = :org_id"),
        {"id": scan_id, "org_id": user.org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Scan nao encontrado")
    return dict(row)


@router.get("/dast/scan/{scan_id}/findings")
def get_dast_findings(
    scan_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Get DAST findings."""
    rows = db.execute(
        text("""
            SELECT * FROM dast_findings
            WHERE scan_id = :scan_id AND org_id = :org_id
            ORDER BY confirmed DESC,
                CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END
        """),
        {"scan_id": scan_id, "org_id": user.org_id},
    ).mappings().all()
    return {"findings": [dict(r) for r in rows]}


@router.get("/dast/scans")
def list_dast_scans(
    page: int = 1,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """List past DAST scans."""
    limit = 20
    offset = (page - 1) * limit
    rows = db.execute(
        text("""
            SELECT * FROM dast_scans
            WHERE product_id = :product_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"product_id": product.id, "limit": limit, "offset": offset},
    ).mappings().all()

    total = db.execute(
        text("SELECT COUNT(*) as cnt FROM dast_scans WHERE product_id = :product_id"),
        {"product_id": product.id},
    ).mappings().first()

    return {
        "scans": [dict(r) for r in rows],
        "total": total["cnt"] if total else 0,
        "page": page,
    }


# ────────────────────── PDF Reports ──────────────────────


@router.get("/scan/{scan_id}/report/pdf")
def download_security_pdf(
    scan_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    """Download security audit report as PDF."""
    scan = db.execute(
        text("SELECT * FROM security_scans WHERE id = :id AND org_id = :org_id"),
        {"id": scan_id, "org_id": user.org_id},
    ).mappings().first()
    if not scan:
        raise HTTPException(404, "Scan nao encontrado")

    findings = db.execute(
        text("SELECT * FROM security_findings WHERE scan_id = :id ORDER BY severity"),
        {"id": scan_id},
    ).mappings().all()

    deps = db.execute(
        text("SELECT * FROM dependency_alerts WHERE scan_id = :id ORDER BY severity"),
        {"id": scan_id},
    ).mappings().all()

    from app.core.pdf_generator import PDFGenerator

    pdf = PDFGenerator().generate_security_report(dict(scan), [dict(f) for f in findings], [dict(d) for d in deps])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="security-{scan_id}.pdf"'},
    )


@router.get("/dast/scan/{scan_id}/report/pdf")
def download_dast_pdf(
    scan_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin")),
    product: Product = Depends(get_current_product),
):
    """Download DAST scan report as PDF."""
    scan = db.execute(
        text("SELECT * FROM dast_scans WHERE id = :id AND org_id = :org_id"),
        {"id": scan_id, "org_id": user.org_id},
    ).mappings().first()
    if not scan:
        raise HTTPException(404, "DAST scan nao encontrado")

    findings = db.execute(
        text("SELECT * FROM dast_findings WHERE scan_id = :id ORDER BY severity"),
        {"id": scan_id},
    ).mappings().all()

    from app.core.pdf_generator import PDFGenerator

    pdf = PDFGenerator().generate_dast_report(dict(scan), [dict(f) for f in findings])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="dast-{scan_id}.pdf"'},
    )
