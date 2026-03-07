import hashlib
import hmac
import json
import logging
import tempfile

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from sqlalchemy import text

import uuid

from app.config import settings
from app.core.code_reviewer import CodeReviewer, fetch_pr_info
from app.core.github_commenter import post_review_comment
from app.core.ingestor import delete_chunks_by_file, reindex_files
from app.core.knowledge_extractor import KnowledgeExtractor
from app.db.session import SessionLocal
from app.integrations.github_client import clone_repository

router = APIRouter()
logger = logging.getLogger(__name__)

MAIN_BRANCHES = {"refs/heads/main", "refs/heads/master"}


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _get_org_docs_settings(db, org_id: str) -> dict:
    row = db.execute(
        text("SELECT settings FROM organizations WHERE id = :org_id"),
        {"org_id": org_id},
    ).mappings().first()
    if not row or not row["settings"]:
        return {}
    return row["settings"].get("docs", {})


def _auto_push_readme(db, org_id: str, repo_name: str, doc_id: str):
    """Push README to GitHub automatically after generation."""
    import base64
    import httpx

    doc = db.execute(
        text("SELECT content FROM repo_docs WHERE id = :id"),
        {"id": doc_id},
    ).mappings().first()
    if not doc:
        return

    gh = db.execute(
        text("SELECT github_token FROM github_integration WHERE org_id = :org_id AND is_active = true LIMIT 1"),
        {"org_id": org_id},
    ).mappings().first()
    if not gh:
        return

    token = gh["github_token"]
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    api_url = f"https://api.github.com/repos/{repo_name}/contents/README.md"

    try:
        resp = httpx.get(api_url, headers=headers, timeout=15)
        existing_sha = resp.json().get("sha") if resp.status_code == 200 else None
    except Exception:
        existing_sha = None

    content_b64 = base64.b64encode(doc["content"].encode()).decode()
    payload = {
        "message": "docs: atualiza README via Memora",
        "content": content_b64,
        "committer": {"name": "Memora Bot", "email": "memora@noreply.local"},
    }
    if existing_sha:
        payload["sha"] = existing_sha

    try:
        httpx.put(api_url, headers=headers, json=payload, timeout=30)
        db.execute(text("""
            UPDATE repo_docs SET pushed_to_github = true, pushed_at = now(), updated_at = now()
            WHERE id = :id
        """), {"id": doc_id})
        db.commit()
        logger.info(f"Auto-push README: {repo_name}")
    except Exception as e:
        logger.error(f"Auto-push README failed: {e}")


def _get_org_knowledge_settings(db, org_id: str) -> dict:
    row = db.execute(
        text("SELECT settings FROM organizations WHERE id = :org_id"),
        {"org_id": org_id},
    ).mappings().first()
    if not row or not row["settings"]:
        return {}
    return row["settings"].get("knowledge", {})


def _find_org_for_repo(db, repo_name: str) -> str | None:
    """Find org_id that owns this repo via github_integration."""
    owner = repo_name.split("/")[0] if "/" in repo_name else None
    if not owner:
        return None
    row = db.execute(
        text("SELECT org_id FROM github_integration WHERE github_login = :login AND is_active = true LIMIT 1"),
        {"login": owner},
    ).mappings().first()
    return row["org_id"] if row else None


def _handle_pr_event(data: dict, background_tasks: BackgroundTasks) -> dict:
    """Handle pull_request webhook events."""
    action = data.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "reason": f"PR action {action} not handled"}

    pr = data.get("pull_request", {})
    repo = data.get("repository", {})
    repo_full_name = repo.get("full_name", "")
    pr_number = pr.get("number")

    if not repo_full_name or not pr_number:
        return {"status": "ignored", "reason": "missing repo or PR number"}

    logger.info(f"Webhook PR {action}: {repo_full_name}#{pr_number}")

    background_tasks.add_task(
        _process_pr, repo_full_name, pr_number, pr.get("title", ""),
        pr.get("user", {}).get("login", ""), pr.get("html_url", ""),
    )

    return {
        "status": "processing",
        "event": "pull_request",
        "action": action,
        "pr_number": pr_number,
    }


def _process_pr(repo_full_name: str, pr_number: int, pr_title: str, pr_author: str, pr_url: str):
    """Process PR event in background — create review and analyze."""
    db = SessionLocal()
    try:
        org_id = _find_org_for_repo(db, repo_full_name)
        if not org_id:
            logger.warning(f"No org found for repo {repo_full_name}")
            return

        # Check if auto-review is enabled
        org_row = db.execute(
            text("SELECT settings FROM organizations WHERE id = :org_id"),
            {"org_id": org_id},
        ).mappings().first()

        if org_row and org_row.get("settings"):
            review_settings = org_row["settings"].get("code_review", {})
            if not review_settings.get("auto_review", True):
                logger.info(f"Auto-review disabled for org {org_id}, skipping PR {pr_number}")
                return

        custom_instructions = None
        if org_row and org_row.get("settings"):
            review_settings = org_row["settings"].get("code_review", {})
            custom_instructions = review_settings.get("custom_instructions")

        # Fetch PR files
        pr_info = fetch_pr_info(db, org_id, repo_full_name, pr_number)
        files_changed = pr_info["files_changed"] if pr_info else []

        review_id = str(uuid.uuid4())
        db.execute(text("""
            INSERT INTO code_reviews
                (id, org_id, repo_id, source_type, pr_number, pr_title, pr_url, pr_author,
                 files_changed, status, custom_instructions)
            VALUES (:id, :org_id, :repo_id, 'pr', :pr_number, :pr_title, :pr_url, :pr_author,
                    :files_changed, 'pending', :custom_instructions)
        """), {
            "id": review_id,
            "org_id": org_id,
            "repo_id": repo_full_name,
            "pr_number": pr_number,
            "pr_title": pr_title,
            "pr_url": pr_url,
            "pr_author": pr_author,
            "files_changed": json.dumps(files_changed) if files_changed else None,
            "custom_instructions": custom_instructions,
        })
        db.commit()

        # Run analysis
        reviewer = CodeReviewer(db, org_id)
        result = reviewer.review(review_id)
        logger.info(f"PR review completed: {repo_full_name}#{pr_number} — score {result['score']}")

        # Post comment on GitHub
        app_url = getattr(settings, "app_url", "http://localhost:3000")
        post_review_comment(db, org_id, review_id, app_url)

    except Exception as e:
        logger.error(f"PR review failed for {repo_full_name}#{pr_number}: {e}")
    finally:
        db.close()


def _process_push(repo_name: str, clone_url: str, added_or_modified: list[str], removed: list[str]):
    """Processa push event em background — re-indexa e deleta conforme necessário."""
    db = SessionLocal()
    try:
        org_id = _find_org_for_repo(db, repo_name)
        if not org_id:
            logger.warning(f"Org nao encontrada para repo {repo_name} — ignorando push")
            return

        # Deletar chunks de arquivos removidos
        for file_path in removed:
            delete_chunks_by_file(db, repo_name, file_path, org_id=org_id)

        # Re-indexar arquivos adicionados/modificados
        if added_or_modified:
            repo_path = clone_repository(clone_url, db)
            result = reindex_files(
                db=db,
                repo_name=repo_name,
                repo_path=repo_path,
                file_paths=added_or_modified,
                org_id=org_id,
            )
            logger.info(f"Webhook re-indexação concluída: {result}")

        logger.info(
            f"Webhook processado: {repo_name} — "
            f"{len(added_or_modified)} re-indexados, {len(removed)} removidos"
        )
        if org_id:
            ks = _get_org_knowledge_settings(db, org_id)

            if ks.get("auto_sync", False):
                try:
                    extractor = KnowledgeExtractor(db, org_id)
                    sync_result = extractor.sync_all(repo_name)
                    logger.info(f"Webhook auto-sync: {repo_name} — {sync_result}")
                except Exception as e:
                    logger.error(f"Webhook auto-sync failed: {e}")

            # Wiki generation is now suggestion-based — admin approves via UI

            # Auto-regenerate docs (README + onboarding) if configured
            ds = _get_org_docs_settings(db, org_id)
            if ds.get("auto_generate_readme", False):
                try:
                    from app.core.readme_generator import ReadmeGenerator
                    readme_gen = ReadmeGenerator(db, org_id)
                    readme_result = readme_gen.generate(repo_name, trigger="push")
                    logger.info(f"Webhook auto-readme: {repo_name} — {readme_result}")

                    # Auto-push to GitHub if configured
                    if ds.get("auto_push_readme", False) and "doc_id" in readme_result:
                        _auto_push_readme(db, org_id, repo_name, readme_result["doc_id"])

                except Exception as e:
                    logger.error(f"Webhook auto-readme failed: {e}")

                try:
                    from app.core.onboarding_generator import OnboardingGenerator
                    onboard_gen = OnboardingGenerator(db, org_id)
                    onboard_result = onboard_gen.generate(repo_name, trigger="push")
                    logger.info(f"Webhook auto-onboarding: {repo_name} — {onboard_result}")
                except Exception as e:
                    logger.error(f"Webhook auto-onboarding failed: {e}")

            # Detect business rule changes
            try:
                from app.core.rules_change_detector import RulesChangeDetector
                detector = RulesChangeDetector(db, org_id)
                alerts = detector.detect_changes(repo_name, list(added_or_modified))
                if alerts:
                    logger.info(f"Webhook rule changes: {repo_name} — {len(alerts)} alertas")
            except Exception as e:
                logger.error(f"Webhook rule change detection failed: {e}")

    except Exception as e:
        logger.error(f"Erro ao processar webhook de {repo_name}: {e}")
    finally:
        db.close()


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
):
    payload = await request.body()

    # Validação de assinatura
    if settings.github_webhook_secret:
        if not x_hub_signature_256 or not verify_github_signature(
            payload, x_hub_signature_256, settings.github_webhook_secret
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()

    # Handle pull_request events
    if x_github_event == "pull_request":
        return _handle_pr_event(data, background_tasks)

    # Ignora eventos que não são push
    if x_github_event != "push":
        return {"status": "ignored", "event": x_github_event}

    # Filtra apenas push para main/master
    ref = data.get("ref", "")
    if ref not in MAIN_BRANCHES:
        return {"status": "ignored", "reason": f"branch {ref} is not main/master"}

    repo_name = data.get("repository", {}).get("full_name", "")
    clone_url = data.get("repository", {}).get("clone_url", "")

    # Separar arquivos por ação
    added_or_modified: set[str] = set()
    removed: set[str] = set()

    for commit in data.get("commits", []):
        for f in commit.get("added", []):
            if f.endswith(".py"):
                added_or_modified.add(f)
        for f in commit.get("modified", []):
            if f.endswith(".py"):
                added_or_modified.add(f)
        for f in commit.get("removed", []):
            if f.endswith(".py"):
                removed.add(f)

    # Arquivo que foi removido e depois re-adicionado no mesmo push: re-indexar
    removed -= added_or_modified

    total_py = len(added_or_modified) + len(removed)
    if total_py == 0:
        return {"status": "ignored", "reason": "no Python files changed"}

    logger.info(
        f"Webhook push: {repo_name} (ref={ref}) — "
        f"{len(added_or_modified)} para re-indexar, {len(removed)} para remover"
    )

    # Processa em background para responder rápido ao GitHub
    background_tasks.add_task(
        _process_push,
        repo_name,
        clone_url,
        list(added_or_modified),
        list(removed),
    )

    return {
        "status": "processing",
        "repo": repo_name,
        "files_to_reindex": len(added_or_modified),
        "files_to_remove": len(removed),
    }
