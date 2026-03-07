"""Endpoints de Revisao de Codigo (Modulo 4) — admin + dev."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_role
from app.config import settings
from app.core.code_reviewer import CodeReviewer
from app.core.github_commenter import post_review_comment
from app.db.session import SessionLocal
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_role("admin", "dev"))])
logger = logging.getLogger(__name__)


def _get_user(user: User = Depends(require_role("admin", "dev"))) -> User:
    return user


# --- Request models ---

class ManualReviewRequest(BaseModel):
    code: str
    language: str = "python"
    context: str | None = None
    repo_id: str | None = None


# --- Background tasks ---

def _run_review_bg(org_id: str, review_id: str):
    """Run review analysis in background."""
    db = SessionLocal()
    try:
        reviewer = CodeReviewer(db, org_id)
        result = reviewer.review(review_id)
        logger.info(f"Review completed: {review_id} — score {result['score']}")

        # Post GitHub comment if it's a PR review
        review = db.execute(
            text("SELECT source_type, pr_number, repo_id FROM code_reviews WHERE id = :id"),
            {"id": review_id},
        ).mappings().first()

        if review and review["source_type"] == "pr" and review["pr_number"]:
            # Check if auto-comment is enabled
            org_row = db.execute(
                text("SELECT settings FROM organizations WHERE id = :org_id"),
                {"org_id": org_id},
            ).mappings().first()

            auto_comment = True
            if org_row and org_row.get("settings"):
                review_settings = org_row["settings"].get("code_review", {})
                auto_comment = review_settings.get("auto_review", True)

            if auto_comment:
                app_url = settings.app_url if hasattr(settings, "app_url") else "http://localhost:3000"
                post_review_comment(db, org_id, review_id, app_url)

    except Exception as e:
        logger.error(f"Review background task failed: {e}")
    finally:
        db.close()


# --- Endpoints ---

@router.post("/reviews/manual")
def create_manual_review(
    body: ManualReviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    """Create a manual code review."""
    if not body.code.strip():
        raise HTTPException(status_code=400, detail="Codigo nao pode ser vazio")
    if len(body.code) > 200000:
        raise HTTPException(status_code=400, detail="Codigo muito grande (max 200KB)")

    # Get custom instructions from org settings
    org_row = db.execute(
        text("SELECT settings FROM organizations WHERE id = :org_id"),
        {"org_id": user.org_id},
    ).mappings().first()

    custom_instructions = None
    if org_row and org_row.get("settings"):
        review_settings = org_row["settings"].get("code_review", {})
        custom_instructions = review_settings.get("custom_instructions")

    review_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO code_reviews
            (id, org_id, source_type, submitted_by, code_snippet, language,
             status, custom_instructions, repo_id)
        VALUES (:id, :org_id, 'manual', :submitted_by, :code, :language,
                'pending', :custom_instructions, :repo_id)
    """), {
        "id": review_id,
        "org_id": user.org_id,
        "submitted_by": user.id,
        "code": body.code,
        "language": body.language,
        "custom_instructions": custom_instructions,
        "repo_id": body.repo_id,
    })
    db.commit()

    background_tasks.add_task(_run_review_bg, user.org_id, review_id)

    return {"review_id": review_id, "status": "analyzing"}


@router.get("/reviews")
def list_reviews(
    repo_id: str | None = Query(None),
    source_type: str | None = Query(None),
    verdict: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    """List code reviews for the organization."""
    query = """
        SELECT id, source_type, pr_number, pr_title, pr_url, pr_author,
               status, overall_score, overall_verdict, summary,
               repo_id, language, github_comment_posted, created_at, updated_at
        FROM code_reviews
        WHERE org_id = :org_id
    """
    params: dict = {"org_id": user.org_id}

    if repo_id:
        query += " AND repo_id = :repo_id"
        params["repo_id"] = repo_id
    if source_type:
        query += " AND source_type = :source_type"
        params["source_type"] = source_type
    if verdict:
        query += " AND overall_verdict = :verdict"
        params["verdict"] = verdict

    query += " ORDER BY created_at DESC LIMIT 20 OFFSET :offset"
    params["offset"] = (page - 1) * 20

    rows = db.execute(text(query), params).mappings().all()

    return [
        {
            "id": r["id"],
            "source_type": r["source_type"],
            "pr_number": r["pr_number"],
            "pr_title": r["pr_title"],
            "pr_url": r["pr_url"],
            "pr_author": r["pr_author"],
            "status": r["status"],
            "overall_score": r["overall_score"],
            "overall_verdict": r["overall_verdict"],
            "summary": r["summary"],
            "repo_id": r["repo_id"],
            "language": r["language"],
            "github_comment_posted": r["github_comment_posted"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
            "updated_at": str(r["updated_at"]) if r["updated_at"] else None,
        }
        for r in rows
    ]


@router.get("/reviews/stats")
def review_stats(
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    """Return review statistics."""
    org_id = user.org_id

    stats = db.execute(text("""
        SELECT
            COUNT(*) as total,
            AVG(overall_score) FILTER (WHERE overall_score IS NOT NULL) as avg_score,
            COUNT(*) FILTER (WHERE overall_verdict IN ('approved', 'approved_with_warnings')) as approved_count,
            COUNT(*) FILTER (WHERE created_at > now() - interval '30 days') as this_month
        FROM code_reviews
        WHERE org_id = :org_id AND status = 'completed'
    """), {"org_id": org_id}).mappings().first()

    critical_count = db.execute(text("""
        SELECT COUNT(*) as cnt
        FROM review_findings f
        JOIN code_reviews r ON r.id = f.review_id
        WHERE f.org_id = :org_id AND f.severity = 'critical' AND r.status = 'completed'
    """), {"org_id": org_id}).mappings().first()

    # Weekly trend (last 8 weeks)
    weekly = db.execute(text("""
        SELECT
            date_trunc('week', created_at)::date as week,
            AVG(overall_score) as avg_score,
            COUNT(*) as count
        FROM code_reviews
        WHERE org_id = :org_id AND status = 'completed'
              AND created_at > now() - interval '8 weeks'
        GROUP BY date_trunc('week', created_at)
        ORDER BY week
    """), {"org_id": org_id}).mappings().all()

    # Findings by category
    by_category = db.execute(text("""
        SELECT f.category, COUNT(*) as count
        FROM review_findings f
        JOIN code_reviews r ON r.id = f.review_id
        WHERE f.org_id = :org_id AND r.status = 'completed'
        GROUP BY f.category
    """), {"org_id": org_id}).mappings().all()

    total = stats["total"] or 0
    approved = stats["approved_count"] or 0

    return {
        "total_reviews": total,
        "avg_score": round(float(stats["avg_score"]), 1) if stats["avg_score"] else None,
        "this_month": stats["this_month"] or 0,
        "approval_rate": round(approved / total * 100, 1) if total > 0 else None,
        "critical_findings": critical_count["cnt"] if critical_count else 0,
        "weekly_trend": [
            {
                "week": str(w["week"]),
                "avg_score": round(float(w["avg_score"]), 1) if w["avg_score"] else None,
                "count": w["count"],
            }
            for w in weekly
        ],
        "findings_by_category": {r["category"]: r["count"] for r in by_category},
    }


@router.get("/reviews/{review_id}")
def get_review(
    review_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    """Get review detail with all findings."""
    review = db.execute(
        text("SELECT * FROM code_reviews WHERE id = :id AND org_id = :org_id"),
        {"id": review_id, "org_id": user.org_id},
    ).mappings().first()

    if not review:
        raise HTTPException(status_code=404, detail="Revisao nao encontrada")

    findings = db.execute(
        text("""
            SELECT * FROM review_findings
            WHERE review_id = :review_id
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                category
        """),
        {"review_id": review_id},
    ).mappings().all()

    return {
        "id": review["id"],
        "source_type": review["source_type"],
        "pr_number": review["pr_number"],
        "pr_title": review["pr_title"],
        "pr_url": review["pr_url"],
        "pr_author": review["pr_author"],
        "submitted_by": review["submitted_by"],
        "code_snippet": review["code_snippet"],
        "language": review["language"],
        "diff": review["diff"],
        "files_changed": review["files_changed"],
        "status": review["status"],
        "overall_score": review["overall_score"],
        "overall_verdict": review["overall_verdict"],
        "summary": review["summary"],
        "github_comment_posted": review["github_comment_posted"],
        "created_at": str(review["created_at"]) if review["created_at"] else None,
        "updated_at": str(review["updated_at"]) if review["updated_at"] else None,
        "findings": [
            {
                "id": f["id"],
                "category": f["category"],
                "severity": f["severity"],
                "title": f["title"],
                "description": f["description"],
                "suggestion": f["suggestion"],
                "file_path": f["file_path"],
                "line_start": f["line_start"],
                "line_end": f["line_end"],
                "code_snippet": f["code_snippet"],
            }
            for f in findings
        ],
    }


@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(_get_user),
):
    """Delete a code review and its findings."""
    result = db.execute(
        text("DELETE FROM code_reviews WHERE id = :id AND org_id = :org_id"),
        {"id": review_id, "org_id": user.org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Revisao nao encontrada")
    return {"deleted": True}
