"""Endpoints para Documentacao Automatica e Onboarding."""

import json
import logging
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_role
from app.db.session import SessionLocal
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_role("admin", "dev"))])
public_router = APIRouter(dependencies=[Depends(require_role("admin", "dev", "suporte"))])

logger = logging.getLogger(__name__)


# ---------- Request / Response models ----------

class GenerateRequest(BaseModel):
    doc_type: str  # readme | onboarding_guide | all


class PushToGitHubRequest(BaseModel):
    commit_message: str | None = None


class OnboardingStepRequest(BaseModel):
    step_id: str


# ---------- Background task helpers ----------

def _generate_doc_bg(repo_name: str, doc_type: str, org_id: str, trigger: str = "manual"):
    """Gera documentacao em background."""
    db = SessionLocal()
    try:
        if doc_type in ("readme", "all"):
            from app.core.readme_generator import ReadmeGenerator
            gen = ReadmeGenerator(db, org_id)
            result = gen.generate(repo_name, trigger=trigger)
            logger.info(f"README gerado para {repo_name}: {result}")

        if doc_type in ("onboarding_guide", "all"):
            from app.core.onboarding_generator import OnboardingGenerator
            gen = OnboardingGenerator(db, org_id)
            result = gen.generate(repo_name, trigger=trigger)
            logger.info(f"Onboarding gerado para {repo_name}: {result}")

    except Exception as e:
        logger.error(f"Erro ao gerar doc ({doc_type}) para {repo_name}: {e}")
    finally:
        db.close()


# ---------- Generation endpoints ----------

@router.post("/docs/generate/{repo_name}")
def generate_docs(
    repo_name: str,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    """Dispara geracao de documentacao em background."""
    if body.doc_type not in ("readme", "onboarding_guide", "all"):
        raise HTTPException(status_code=400, detail="doc_type invalido")

    background_tasks.add_task(_generate_doc_bg, repo_name, body.doc_type, user.org_id, "manual")

    return {"status": "generating", "repo_name": repo_name, "doc_type": body.doc_type}


@router.get("/docs/status/{repo_name}")
def get_docs_status(
    repo_name: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retorna status de geracao dos docs do repo."""
    rows = db.execute(text("""
        SELECT doc_type, generated_at, pushed_to_github, pushed_at, content_hash
        FROM repo_docs
        WHERE org_id = :org_id AND repo_name = :repo_name
    """), {"org_id": user.org_id, "repo_name": repo_name}).mappings().all()

    result = {}
    for r in rows:
        result[r["doc_type"]] = {
            "generated_at": str(r["generated_at"]) if r["generated_at"] else None,
            "pushed_to_github": r["pushed_to_github"],
            "pushed_at": str(r["pushed_at"]) if r["pushed_at"] else None,
            "content_hash": r["content_hash"],
        }

    return result


@public_router.get("/docs/{repo_name}/readme")
def get_readme(
    repo_name: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retorna README gerado em markdown."""
    row = db.execute(text("""
        SELECT id, content, generated_at, pushed_to_github, pushed_at, content_hash,
               generation_trigger, created_at, updated_at
        FROM repo_docs
        WHERE org_id = :org_id AND repo_name = :repo_name AND doc_type = 'readme'
        LIMIT 1
    """), {"org_id": user.org_id, "repo_name": repo_name}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="README ainda nao gerado")

    return {
        "id": row["id"],
        "content": row["content"],
        "generated_at": str(row["generated_at"]) if row["generated_at"] else None,
        "pushed_to_github": row["pushed_to_github"],
        "pushed_at": str(row["pushed_at"]) if row["pushed_at"] else None,
        "content_hash": row["content_hash"],
        "generation_trigger": row["generation_trigger"],
    }


@public_router.get("/docs/{repo_name}/onboarding")
def get_onboarding(
    repo_name: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retorna guia de onboarding em markdown."""
    row = db.execute(text("""
        SELECT id, content, generated_at, content_hash, generation_trigger, created_at, updated_at
        FROM repo_docs
        WHERE org_id = :org_id AND repo_name = :repo_name AND doc_type = 'onboarding_guide'
        LIMIT 1
    """), {"org_id": user.org_id, "repo_name": repo_name}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Guia de onboarding ainda nao gerado")

    return {
        "id": row["id"],
        "content": row["content"],
        "generated_at": str(row["generated_at"]) if row["generated_at"] else None,
        "content_hash": row["content_hash"],
        "generation_trigger": row["generation_trigger"],
    }


# ---------- Push to GitHub ----------

@router.post("/docs/{repo_name}/push-to-github")
def push_readme_to_github(
    repo_name: str,
    body: PushToGitHubRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin")),
):
    """Faz push do README gerado para o repositorio no GitHub."""
    # Busca README gerado
    doc = db.execute(text("""
        SELECT id, content FROM repo_docs
        WHERE org_id = :org_id AND repo_name = :repo_name AND doc_type = 'readme'
        LIMIT 1
    """), {"org_id": user.org_id, "repo_name": repo_name}).mappings().first()

    if not doc:
        raise HTTPException(status_code=404, detail="README nao encontrado. Gere primeiro.")

    # Busca token GitHub
    gh = db.execute(text("""
        SELECT github_token, github_login FROM github_integration
        WHERE org_id = :org_id AND is_active = true
        LIMIT 1
    """), {"org_id": user.org_id}).mappings().first()

    if not gh:
        raise HTTPException(status_code=400, detail="GitHub nao conectado")

    token = gh["github_token"]
    commit_msg = body.commit_message or "docs: atualiza README via Memora"

    # Verifica se README ja existe (precisa do sha para update)
    import base64
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    api_url = f"https://api.github.com/repos/{repo_name}/contents/README.md"

    try:
        resp = httpx.get(api_url, headers=headers, timeout=15)
        existing_sha = resp.json().get("sha") if resp.status_code == 200 else None
    except Exception:
        existing_sha = None

    # PUT para criar/atualizar
    content_b64 = base64.b64encode(doc["content"].encode()).decode()
    payload = {
        "message": commit_msg,
        "content": content_b64,
        "committer": {"name": "Memora Bot", "email": "memora@noreply.local"},
    }
    if existing_sha:
        payload["sha"] = existing_sha

    try:
        resp = httpx.put(api_url, headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"GitHub API error: {resp.status_code} — {resp.text[:200]}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao conectar com GitHub: {e}")

    # Marca como pushed
    db.execute(text("""
        UPDATE repo_docs SET pushed_to_github = true, pushed_at = now(), updated_at = now()
        WHERE id = :id
    """), {"id": doc["id"]})
    db.commit()

    return {"status": "pushed", "repo_name": repo_name, "commit_message": commit_msg}


# ---------- Onboarding progress ----------

@public_router.get("/onboarding/{repo_name}/progress")
def get_onboarding_progress(
    repo_name: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retorna progresso de onboarding do usuario autenticado."""
    row = db.execute(text("""
        SELECT op.id, op.steps_total, op.steps_completed, op.completed_steps,
               op.started_at, op.completed_at
        FROM onboarding_progress op
        WHERE op.org_id = :org_id AND op.user_id = :user_id AND op.repo_name = :repo_name
        LIMIT 1
    """), {
        "org_id": user.org_id,
        "user_id": user.id,
        "repo_name": repo_name,
    }).mappings().first()

    if not row:
        return {
            "started": False,
            "steps_total": 0,
            "steps_completed": 0,
            "completed_steps": [],
        }

    return {
        "started": True,
        "steps_total": row["steps_total"],
        "steps_completed": row["steps_completed"],
        "completed_steps": row["completed_steps"] or [],
        "started_at": str(row["started_at"]) if row["started_at"] else None,
        "completed_at": str(row["completed_at"]) if row["completed_at"] else None,
    }


@public_router.post("/onboarding/{repo_name}/progress")
def update_onboarding_progress(
    repo_name: str,
    body: OnboardingStepRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Marca step como concluido para o usuario autenticado."""
    # Busca guia de onboarding
    guide = db.execute(text("""
        SELECT id, content FROM repo_docs
        WHERE org_id = :org_id AND repo_name = :repo_name AND doc_type = 'onboarding_guide'
        LIMIT 1
    """), {"org_id": user.org_id, "repo_name": repo_name}).mappings().first()

    if not guide:
        raise HTTPException(status_code=404, detail="Guia de onboarding nao encontrado")

    # Conta passos do guia
    steps_total = guide["content"].lower().count("### passo")
    if steps_total < 1:
        steps_total = 5

    # Busca ou cria progresso
    existing = db.execute(text("""
        SELECT id, completed_steps, steps_completed
        FROM onboarding_progress
        WHERE org_id = :org_id AND user_id = :user_id AND repo_name = :repo_name
        LIMIT 1
    """), {
        "org_id": user.org_id,
        "user_id": user.id,
        "repo_name": repo_name,
    }).mappings().first()

    if existing:
        completed = existing["completed_steps"] or []
        if body.step_id not in completed:
            completed.append(body.step_id)

        is_done = len(completed) >= steps_total
        db.execute(text("""
            UPDATE onboarding_progress
            SET completed_steps = :steps, steps_completed = :count,
                completed_at = CASE WHEN :is_done THEN now() ELSE completed_at END,
                updated_at = now()
            WHERE id = :id
        """), {
            "steps": json.dumps(completed),
            "count": len(completed),
            "is_done": is_done,
            "id": existing["id"],
        })
    else:
        progress_id = str(uuid.uuid4())
        completed = [body.step_id]
        is_done = len(completed) >= steps_total
        db.execute(text("""
            INSERT INTO onboarding_progress
                (id, org_id, user_id, repo_name, guide_id, steps_total, steps_completed,
                 completed_steps, completed_at)
            VALUES (:id, :org_id, :user_id, :repo_name, :guide_id, :steps_total, :count,
                    :steps, CASE WHEN :is_done THEN now() ELSE NULL END)
        """), {
            "id": progress_id,
            "org_id": user.org_id,
            "user_id": user.id,
            "repo_name": repo_name,
            "guide_id": guide["id"],
            "steps_total": steps_total,
            "count": len(completed),
            "steps": json.dumps(completed),
            "is_done": is_done,
        })

    db.commit()

    return {
        "steps_total": steps_total,
        "steps_completed": len(completed),
        "completed_steps": completed,
        "is_complete": len(completed) >= steps_total,
    }
