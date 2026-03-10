import json
import os
import queue
import shutil
import threading

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_data_session, require_role
from app.core.ingestor import ingest_repository
from app.core.rate_limit import INGEST_LIMIT, limiter
from app.integrations.github_client import clone_repository
from app.models.product import Product
from app.models.user import User

MAX_REPO_SIZE_MB = 500
MAX_REPO_FILES = 50_000

router = APIRouter()


class IngestRequest(BaseModel):
    repo_path: str
    repo_name: str | None = None


class IngestResponse(BaseModel):
    repo_name: str
    files_processed: int
    chunks_created: int


def _check_github_repo_size(repo_url: str) -> None:
    """Verifica tamanho do repo via GitHub API antes de clonar."""
    # Extrair owner/repo da URL
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return
    owner, repo = parts[-2], parts[-1].replace(".git", "")
    try:
        resp = httpx.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=10)
        if resp.status_code == 200:
            size_kb = resp.json().get("size", 0)
            size_mb = size_kb / 1024
            if size_mb > MAX_REPO_SIZE_MB:
                raise HTTPException(
                    status_code=400,
                    detail=f"Repositório excede o limite de {MAX_REPO_SIZE_MB}MB ({size_mb:.0f}MB). "
                           "Reduza o escopo ou entre em contato com o suporte.",
                )
    except HTTPException:
        raise
    except Exception:
        pass  # Se não conseguir verificar, prossegue


def _check_local_repo_size(path: str) -> None:
    """Verifica tamanho e quantidade de arquivos de um diretório local."""
    total_size = 0
    file_count = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        # Ignorar .git
        if "/.git" in dirpath or "\\.git" in dirpath:
            continue
        file_count += len(filenames)
        if file_count > MAX_REPO_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Repositório excede o limite de {MAX_REPO_FILES:,} arquivos. "
                       "Reduza o escopo ou use .gitignore.",
            )
        for f in filenames:
            try:
                total_size += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    size_mb = total_size / (1024 * 1024)
    if size_mb > MAX_REPO_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Repositório excede o limite de {MAX_REPO_SIZE_MB}MB ({size_mb:.0f}MB).",
        )


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit(INGEST_LIMIT)
def ingest(
    request: Request,
    body: IngestRequest,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    repo_path = body.repo_path
    cloned_dir = None

    # Se é URL do GitHub, verifica tamanho antes de clonar
    if repo_path.startswith("https://github.com/"):
        _check_github_repo_size(repo_path)
        cloned_dir = clone_repository(repo_path, db)
        repo_path = cloned_dir
        _check_local_repo_size(repo_path)
    else:
        _check_local_repo_size(repo_path)

    try:
        result = ingest_repository(
            db=db,
            repo_path=repo_path,
            repo_name=body.repo_name,
            org_id=user.org_id,
            product_id=product.id,
        )
        return result
    finally:
        if cloned_dir:
            shutil.rmtree(cloned_dir, ignore_errors=True)


@router.post("/ingest/stream")
@limiter.limit(INGEST_LIMIT)
def ingest_stream(
    request: Request,
    body: IngestRequest,
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev")),
    product: Product = Depends(get_current_product),
):
    progress_queue: queue.Queue = queue.Queue()

    def on_progress(stage: str, percent: int, detail: str = ""):
        progress_queue.put({"type": "progress", "stage": stage, "percent": percent, "detail": detail})

    def run_ingest():
        repo_path = body.repo_path
        cloned_dir = None

        try:
            if repo_path.startswith("https://github.com/"):
                on_progress("validating", 1, "Verificando tamanho do repositório...")
                _check_github_repo_size(repo_path)
                on_progress("cloning", 2, "Clonando repositório...")
                cloned_dir = clone_repository(repo_path, db)
                local_path = cloned_dir
                _check_local_repo_size(local_path)
            else:
                _check_local_repo_size(repo_path)
                local_path = repo_path

            result = ingest_repository(
                db=db,
                repo_path=local_path,
                repo_name=body.repo_name,
                org_id=user.org_id,
                product_id=product.id,
                on_progress=on_progress,
            )
            progress_queue.put({"type": "result", **result})
        except Exception as e:
            progress_queue.put({"type": "error", "message": str(e)})
        finally:
            if cloned_dir:
                shutil.rmtree(cloned_dir, ignore_errors=True)
            progress_queue.put(None)  # sentinel

    thread = threading.Thread(target=run_ingest, daemon=True)
    thread.start()

    def event_stream():
        while True:
            try:
                msg = progress_queue.get(timeout=120)
            except queue.Empty:
                break
            if msg is None:
                yield "data: [DONE]\n\n"
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
