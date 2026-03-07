import json
import queue
import shutil
import threading

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_role
from app.core.ingestor import ingest_repository
from app.integrations.github_client import clone_repository
from app.models.user import User

router = APIRouter()


class IngestRequest(BaseModel):
    repo_path: str
    repo_name: str | None = None


class IngestResponse(BaseModel):
    repo_name: str
    files_processed: int
    chunks_created: int


@router.post("/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    repo_path = request.repo_path
    cloned_dir = None

    # Se é URL do GitHub, clona primeiro
    if repo_path.startswith("https://github.com/"):
        cloned_dir = clone_repository(repo_path, db)
        repo_path = cloned_dir

    try:
        result = ingest_repository(
            db=db,
            repo_path=repo_path,
            repo_name=request.repo_name,
            org_id=user.org_id,
        )
        return result
    finally:
        if cloned_dir:
            shutil.rmtree(cloned_dir, ignore_errors=True)


@router.post("/ingest/stream")
def ingest_stream(
    request: IngestRequest,
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    progress_queue: queue.Queue = queue.Queue()

    def on_progress(stage: str, percent: int, detail: str = ""):
        progress_queue.put({"type": "progress", "stage": stage, "percent": percent, "detail": detail})

    def run_ingest():
        repo_path = request.repo_path
        cloned_dir = None

        try:
            if repo_path.startswith("https://github.com/"):
                on_progress("cloning", 2, "Clonando repositório...")
                cloned_dir = clone_repository(repo_path, db)
                local_path = cloned_dir
            else:
                local_path = repo_path

            result = ingest_repository(
                db=db,
                repo_path=local_path,
                repo_name=request.repo_name,
                org_id=user.org_id,
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
