"""Posta comentarios de revisao de codigo em PRs do GitHub."""

import logging

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

VERDICT_DISPLAY = {
    "approved": ("✅", "Aprovado"),
    "approved_with_warnings": ("⚠️", "Aprovado com ressalvas"),
    "needs_changes": ("🔧", "Precisa de alteracoes"),
    "rejected": ("❌", "Rejeitado"),
}

CATEGORY_DISPLAY = {
    "bug": ("🐛", "Bugs"),
    "security": ("🔒", "Seguranca"),
    "performance": ("⚡", "Performance"),
    "consistency": ("🔗", "Consistencia"),
    "pattern": ("📐", "Padroes"),
}

SEVERITY_DISPLAY = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


def post_review_comment(db: Session, org_id: str, review_id: str, app_url: str = "http://localhost:3000") -> bool:
    """Post formatted review comment on the GitHub PR."""
    # Load review
    review = db.execute(
        text("SELECT * FROM code_reviews WHERE id = :id AND org_id = :org_id"),
        {"id": review_id, "org_id": org_id},
    ).mappings().first()

    if not review or review["source_type"] != "pr" or not review["pr_number"]:
        return False

    if not review["overall_score"] and review["overall_score"] != 0:
        return False

    # Load findings
    findings = db.execute(
        text("SELECT * FROM review_findings WHERE review_id = :review_id ORDER BY severity, category"),
        {"review_id": review_id},
    ).mappings().all()

    # Get GitHub token
    gh = db.execute(
        text("SELECT github_token FROM github_integration WHERE org_id = :org_id AND is_active = true LIMIT 1"),
        {"org_id": org_id},
    ).mappings().first()

    if not gh:
        logger.warning("No GitHub token for comment posting")
        return False

    # Check minimum severity setting
    org_row = db.execute(
        text("SELECT settings FROM organizations WHERE id = :org_id"),
        {"org_id": org_id},
    ).mappings().first()

    min_severity = "info"
    if org_row and org_row.get("settings"):
        review_settings = org_row["settings"].get("code_review", {})
        min_severity = review_settings.get("min_comment_severity", "info")

    severity_order = ["critical", "high", "medium", "low", "info"]
    min_idx = severity_order.index(min_severity) if min_severity in severity_order else 4
    visible_findings = [f for f in findings if severity_order.index(f["severity"]) <= min_idx]

    if not visible_findings and review["overall_verdict"] == "approved":
        # No findings worth reporting and code is approved — skip comment
        return False

    # Build markdown comment
    comment = _build_comment(review, visible_findings, app_url)

    # Post to GitHub
    token = gh["github_token"]
    repo_full_name = review["repo_id"]
    pr_number = review["pr_number"]

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        resp = requests.post(
            f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments",
            headers=headers,
            json={"body": comment},
            timeout=30,
        )
        resp.raise_for_status()
        comment_data = resp.json()

        # Save comment ID
        db.execute(text("""
            UPDATE code_reviews
            SET github_comment_id = :comment_id, github_comment_posted = true, updated_at = now()
            WHERE id = :id
        """), {
            "comment_id": str(comment_data.get("id", "")),
            "id": review_id,
        })
        db.commit()

        logger.info(f"Posted review comment on {repo_full_name}#{pr_number}")
        return True

    except Exception as e:
        logger.error(f"Failed to post GitHub comment: {e}")
        return False


def _build_comment(review: dict, findings: list, app_url: str) -> str:
    """Build the formatted markdown comment for GitHub."""
    verdict = review["overall_verdict"] or "pending"
    emoji, label = VERDICT_DISPLAY.get(verdict, ("❓", verdict))
    score = review["overall_score"] or 0

    lines = [
        f"## 🔍 Revisao Memora",
        f"",
        f"**Resultado:** {emoji} {label} — Score: {score}/100",
        f"",
    ]

    if review["summary"]:
        lines.append(review["summary"])
        lines.append("")

    if findings:
        lines.append("---")
        lines.append(f"### Findings ({len(findings)} encontrados)")
        lines.append("")

        # Group by category
        by_category: dict[str, list] = {}
        for f in findings:
            cat = f["category"]
            by_category.setdefault(cat, []).append(f)

        for category in ["bug", "security", "performance", "consistency", "pattern"]:
            cat_findings = by_category.get(category, [])
            if not cat_findings:
                continue

            cat_emoji, cat_label = CATEGORY_DISPLAY.get(category, ("📋", category))
            lines.append(f"#### {cat_emoji} {cat_label} ({len(cat_findings)})")
            lines.append("")

            for f in cat_findings:
                sev_emoji = SEVERITY_DISPLAY.get(f["severity"], "⚪")
                lines.append(f"- **{sev_emoji} [{f['severity'].upper()}] {f['title']}**")

                if f.get("file_path"):
                    loc = f["file_path"]
                    if f.get("line_start"):
                        loc += f":{f['line_start']}"
                    lines.append(f"  `{loc}`")

                lines.append(f"  {f['description']}")

                if f.get("suggestion"):
                    lines.append(f"  💡 *Sugestao: {f['suggestion']}*")

                lines.append("")

    lines.append("---")
    lines.append(f"*Revisao automatica pelo [Memora]({app_url}). Ver detalhes completos no painel.*")

    return "\n".join(lines)
