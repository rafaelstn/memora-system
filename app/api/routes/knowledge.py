"""Endpoints da Memoria Tecnica (Modulo 3) — admin + dev."""

import json
import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_data_session, require_role
from app.config import settings
from app.core.document_processor import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, DocumentProcessor, get_upload_path
from app.core.embedder import Embedder
from app.core.knowledge_extractor import KnowledgeExtractor
from app.core.wiki_generator import WikiGenerator
from app.db.session import SessionLocal
from app.models.product import Product
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_role("admin", "dev"))])
logger = logging.getLogger(__name__)

# Read-only routes (any authenticated user)
public_router = APIRouter()


def _get_user(user: User = Depends(require_role("admin", "dev"))) -> User:
    return user


# ===== Knowledge Search (any authenticated user) =====

@public_router.get("/knowledge/search")
def search_knowledge(
    q: str = Query(..., min_length=2),
    repo_id: str | None = Query(None),
    source_type: str | None = Query(None),
    decision_type: str | None = Query(None),
    db: Session = Depends(get_data_session),
    user: User = Depends(require_role("admin", "dev", "suporte")),
    product: Product = Depends(get_current_product),
):
    """Hybrid search across knowledge entries (semantic + full-text with RRF)."""
    embedder = Embedder()
    query_embedding = embedder.embed_text(q)

    # Semantic search
    sem_where = "WHERE product_id = :product_id"
    sem_params: dict = {"product_id": product.id, "embedding": str(query_embedding), "top_k": 20}
    if repo_id:
        sem_where += " AND repo_id = :repo_id"
        sem_params["repo_id"] = repo_id
    if source_type:
        sem_where += " AND source_type = :source_type"
        sem_params["source_type"] = source_type
    if decision_type:
        sem_where += " AND decision_type = :decision_type"
        sem_params["decision_type"] = decision_type

    semantic_rows = db.execute(text(f"""
        SELECT id, title, summary, source_type, source_url, source_date, decision_type,
               1 - (embedding <=> CAST(:embedding AS vector)) AS score
        FROM knowledge_entries
        {sem_where} AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), sem_params).mappings().all()

    # Keyword search
    kw_where = "WHERE product_id = :product_id"
    kw_params: dict = {"product_id": product.id, "query": q, "top_k": 20}
    if repo_id:
        kw_where += " AND repo_id = :repo_id"
        kw_params["repo_id"] = repo_id
    if source_type:
        kw_where += " AND source_type = :source_type"
        kw_params["source_type"] = source_type
    if decision_type:
        kw_where += " AND decision_type = :decision_type"
        kw_params["decision_type"] = decision_type

    keyword_rows = db.execute(text(f"""
        SELECT id, title, summary, source_type, source_url, source_date, decision_type,
               ts_rank(
                   setweight(to_tsvector('portuguese', title), 'A') ||
                   setweight(to_tsvector('portuguese', COALESCE(summary, '')), 'B'),
                   plainto_tsquery('portuguese', :query)
               ) AS score
        FROM knowledge_entries
        {kw_where}
          AND (
              to_tsvector('portuguese', title) @@ plainto_tsquery('portuguese', :query)
              OR to_tsvector('portuguese', COALESCE(summary, '')) @@ plainto_tsquery('portuguese', :query)
          )
        ORDER BY score DESC
        LIMIT :top_k
    """), kw_params).mappings().all()

    # RRF fusion
    RRF_K = 60
    rrf_scores: dict[str, float] = {}
    entry_data: dict[str, dict] = {}

    for rank, row in enumerate(semantic_rows):
        eid = row["id"]
        rrf_scores[eid] = rrf_scores.get(eid, 0) + 1.0 / (RRF_K + rank + 1)
        entry_data[eid] = dict(row)

    for rank, row in enumerate(keyword_rows):
        eid = row["id"]
        rrf_scores[eid] = rrf_scores.get(eid, 0) + 1.0 / (RRF_K + rank + 1)
        if eid not in entry_data:
            entry_data[eid] = dict(row)

    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:10]

    results = []
    for eid in sorted_ids:
        e = entry_data[eid]
        results.append({
            "id": e["id"],
            "title": e["title"],
            "summary": (e.get("summary") or "")[:300],
            "source_type": e["source_type"],
            "source_url": e.get("source_url"),
            "source_date": str(e["source_date"]) if e.get("source_date") else None,
            "decision_type": e.get("decision_type"),
            "score": round(rrf_scores[eid], 6),
        })

    return results


# ===== Entries CRUD =====

@router.get("/knowledge/entries")
def list_entries(
    repo_id: str | None = Query(None),
    source_type: str | None = Query(None),
    decision_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    per_page = 50
    offset = (page - 1) * per_page
    query = "SELECT id, title, summary, source_type, source_url, source_date, decision_type, file_paths, components, created_at FROM knowledge_entries WHERE product_id = :product_id"
    params: dict = {"product_id": product.id, "limit": per_page, "offset": offset}

    if repo_id:
        query += " AND repo_id = :repo_id"
        params["repo_id"] = repo_id
    if source_type:
        query += " AND source_type = :source_type"
        params["source_type"] = source_type
    if decision_type:
        query += " AND decision_type = :decision_type"
        params["decision_type"] = decision_type

    query += " ORDER BY source_date DESC NULLS LAST, created_at DESC LIMIT :limit OFFSET :offset"
    rows = db.execute(text(query), params).mappings().all()

    return [
        {
            "id": r["id"],
            "title": r["title"],
            "summary": (r.get("summary") or "")[:300],
            "source_type": r["source_type"],
            "source_url": r.get("source_url"),
            "source_date": str(r["source_date"]) if r.get("source_date") else None,
            "decision_type": r.get("decision_type"),
            "file_paths": r.get("file_paths"),
            "components": r.get("components"),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


@router.get("/knowledge/entries/{entry_id}")
def get_entry(entry_id: str, db: Session = Depends(get_data_session), user: User = Depends(_get_user), product: Product = Depends(get_current_product)):
    row = db.execute(
        text("SELECT * FROM knowledge_entries WHERE id = :id AND product_id = :product_id"),
        {"id": entry_id, "product_id": product.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Entrada nao encontrada")
    result = dict(row)
    for k in ("extracted_at", "source_date", "created_at", "updated_at"):
        if result.get(k):
            result[k] = str(result[k])
    # Remove embedding from response
    result.pop("embedding", None)
    return result


# ===== Timeline =====

@router.get("/knowledge/timeline")
def get_timeline(
    repo_id: str | None = Query(None),
    file_path: str | None = Query(None),
    source_type: str | None = Query(None),
    period: str = Query("90d"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    per_page = 50
    offset = (page - 1) * per_page
    query = """
        SELECT id, title, summary, source_type, source_url, source_date,
               decision_type, file_paths, components, created_at
        FROM knowledge_entries
        WHERE product_id = :product_id
    """
    params: dict = {"product_id": product.id, "limit": per_page, "offset": offset}

    if repo_id:
        query += " AND repo_id = :repo_id"
        params["repo_id"] = repo_id
    if file_path:
        query += " AND file_paths::text LIKE :file_path"
        params["file_path"] = f"%{file_path}%"
    if source_type:
        query += " AND source_type = :source_type"
        params["source_type"] = source_type

    # Period filter
    period_map = {"30d": "30 days", "90d": "90 days", "1y": "1 year"}
    if period in period_map:
        query += f" AND COALESCE(source_date, created_at) >= now() - interval '{period_map[period]}'"

    query += " ORDER BY COALESCE(source_date, created_at) DESC LIMIT :limit OFFSET :offset"
    rows = db.execute(text(query), params).mappings().all()

    return [
        {
            "id": r["id"],
            "title": r["title"],
            "summary": (r.get("summary") or "")[:200],
            "source_type": r["source_type"],
            "source_url": r.get("source_url"),
            "source_date": str(r["source_date"]) if r.get("source_date") else None,
            "decision_type": r.get("decision_type"),
            "file_paths": r.get("file_paths"),
            "components": r.get("components"),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ===== ADRs (Architecture Decision Records) =====

class ADRCreate(BaseModel):
    title: str
    content: str
    repo_id: str | None = None
    file_paths: list[str] | None = None
    decision_type: str = "arquitetura"


class ADRUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    file_paths: list[str] | None = None
    decision_type: str | None = None


@router.post("/knowledge/adrs")
def create_adr(
    body: ADRCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    entry_id = str(uuid.uuid4())

    # Generate summary with LLM in background, but save immediately with content as summary
    embedder = Embedder()
    embed_text = f"{body.title}\n{body.content[:2000]}"
    embedding = embedder.embed_text(embed_text)

    db.execute(text("""
        INSERT INTO knowledge_entries
            (id, product_id, repo_id, source_type, title, content, summary,
             embedding, file_paths, decision_type, created_by)
        VALUES
            (:id, :product_id, :repo_id, 'adr', :title, :content, :summary,
             CAST(:embedding AS vector), :file_paths, :decision_type, :created_by)
    """), {
        "id": entry_id,
        "product_id": product.id,
        "repo_id": body.repo_id,
        "title": body.title,
        "content": body.content,
        "summary": body.content[:500],
        "embedding": str(embedding),
        "file_paths": json.dumps(body.file_paths) if body.file_paths else None,
        "decision_type": body.decision_type,
        "created_by": user.id,
    })
    db.commit()

    # Generate proper summary in background
    background_tasks.add_task(_generate_adr_summary, entry_id, user.org_id)

    return {"id": entry_id, "title": body.title}


def _generate_adr_summary(entry_id: str, org_id: str):
    """Background task to generate ADR summary with LLM."""
    db = SessionLocal()
    try:
        from app.integrations import llm_router as lr

        entry = db.execute(
            text("SELECT title, content FROM knowledge_entries WHERE id = :id"),
            {"id": entry_id},
        ).mappings().first()
        if not entry:
            return

        result = lr.complete(
            db=db,
            system_prompt="Resuma esta decisao tecnica em 2-3 paragrafos em portugues brasileiro.",
            user_message=f"Titulo: {entry['title']}\n\nConteudo:\n{entry['content'][:4000]}",
            org_id=org_id,
            max_tokens=512,
        )

        db.execute(
            text("UPDATE knowledge_entries SET summary = :summary WHERE id = :id"),
            {"summary": result["content"], "id": entry_id},
        )
        db.commit()
    except Exception as e:
        logger.error(f"Error generating ADR summary: {e}")
    finally:
        db.close()


@router.put("/knowledge/adrs/{entry_id}")
def update_adr(
    entry_id: str,
    body: ADRUpdate,
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    existing = db.execute(
        text("SELECT id FROM knowledge_entries WHERE id = :id AND product_id = :product_id AND source_type = 'adr'"),
        {"id": entry_id, "product_id": product.id},
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="ADR nao encontrado")

    updates = []
    params: dict = {"id": entry_id}
    if body.title is not None:
        updates.append("title = :title")
        params["title"] = body.title
    if body.content is not None:
        updates.append("content = :content")
        params["content"] = body.content
    if body.file_paths is not None:
        updates.append("file_paths = :file_paths")
        params["file_paths"] = json.dumps(body.file_paths)
    if body.decision_type is not None:
        updates.append("decision_type = :decision_type")
        params["decision_type"] = body.decision_type

    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    updates.append("updated_at = now()")

    # Re-generate embedding if title or content changed
    if body.title is not None or body.content is not None:
        row = db.execute(
            text("SELECT title, content FROM knowledge_entries WHERE id = :id"),
            {"id": entry_id},
        ).mappings().first()
        new_title = body.title or row["title"]
        new_content = body.content or row["content"]
        embedder = Embedder()
        embedding = embedder.embed_text(f"{new_title}\n{new_content[:2000]}")
        updates.append("embedding = CAST(:embedding AS vector)")
        params["embedding"] = str(embedding)

    db.execute(text(f"UPDATE knowledge_entries SET {', '.join(updates)} WHERE id = :id"), params)
    db.commit()
    return {"updated": True}


@router.delete("/knowledge/adrs/{entry_id}")
def delete_adr(entry_id: str, db: Session = Depends(get_data_session), user: User = Depends(_get_user), product: Product = Depends(get_current_product)):
    result = db.execute(
        text("DELETE FROM knowledge_entries WHERE id = :id AND product_id = :product_id AND source_type = 'adr'"),
        {"id": entry_id, "product_id": product.id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="ADR nao encontrado")
    return {"deleted": True}


# ===== Documents =====

@router.post("/knowledge/documents")
async def upload_document(
    file: UploadFile = File(...),
    repo_id: str | None = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo sem nome")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Tipo nao suportado. Aceitos: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (max 10MB)")

    # Save file
    storage_path = get_upload_path(user.org_id, file.filename)
    with open(storage_path, "wb") as f:
        f.write(content)

    doc_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO knowledge_documents
            (id, product_id, repo_id, filename, file_type, file_size, storage_path, uploaded_by)
        VALUES (:id, :product_id, :repo_id, :filename, :file_type, :file_size, :storage_path, :uploaded_by)
    """), {
        "id": doc_id,
        "product_id": product.id,
        "repo_id": repo_id,
        "filename": file.filename,
        "file_type": ext,
        "file_size": len(content),
        "storage_path": storage_path,
        "uploaded_by": user.id,
    })
    db.commit()

    # Process in background
    background_tasks.add_task(_process_document_bg, doc_id, user.org_id)

    return {"document_id": doc_id, "status": "processing"}


def _process_document_bg(document_id: str, org_id: str):
    db = SessionLocal()
    try:
        processor = DocumentProcessor(db, org_id)
        processor.process(document_id)
    except Exception as e:
        logger.error(f"Background document processing failed: {e}")
    finally:
        db.close()


@router.get("/knowledge/documents")
def list_documents(
    page: int = Query(1, ge=1),
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    per_page = 50
    offset = (page - 1) * per_page
    rows = db.execute(text("""
        SELECT kd.*, u.name as uploaded_by_name
        FROM knowledge_documents kd
        LEFT JOIN users u ON u.id = kd.uploaded_by
        WHERE kd.product_id = :product_id
        ORDER BY kd.created_at DESC
        LIMIT :limit OFFSET :offset
    """), {"product_id": product.id, "limit": per_page, "offset": offset}).mappings().all()

    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "file_type": r["file_type"],
            "file_size": r["file_size"],
            "processed": r["processed"],
            "entry_id": r.get("entry_id"),
            "uploaded_by_name": r.get("uploaded_by_name"),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


@router.get("/knowledge/documents/{doc_id}/status")
def document_status(doc_id: str, db: Session = Depends(get_data_session), user: User = Depends(_get_user), product: Product = Depends(get_current_product)):
    row = db.execute(
        text("SELECT processed, entry_id FROM knowledge_documents WHERE id = :id AND product_id = :product_id"),
        {"id": doc_id, "product_id": product.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    return {
        "processed": row["processed"],
        "entry_id": row.get("entry_id"),
        "status": "indexed" if row["processed"] else "processing",
    }


@router.delete("/knowledge/documents/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_data_session), user: User = Depends(_get_user), product: Product = Depends(get_current_product)):
    doc = db.execute(
        text("SELECT storage_path, entry_id FROM knowledge_documents WHERE id = :id AND product_id = :product_id"),
        {"id": doc_id, "product_id": product.id},
    ).mappings().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    # Delete associated knowledge entry if exists
    if doc.get("entry_id"):
        db.execute(text("DELETE FROM knowledge_entries WHERE id = :id"), {"id": doc["entry_id"]})

    db.execute(text("DELETE FROM knowledge_documents WHERE id = :id"), {"id": doc_id})
    db.commit()

    # Delete file
    try:
        if os.path.exists(doc["storage_path"]):
            os.remove(doc["storage_path"])
    except Exception:
        pass

    return {"deleted": True}


# ===== Wiki =====

# File extensions that are NOT code (assets, images, configs, etc.)
_NON_CODE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".lock", ".sum",
}

_NON_CODE_FILENAMES = {
    ".gitignore", ".gitattributes", ".gitmodules", ".editorconfig",
    ".dockerignore", "license", "license.md", "license.txt",
    "changelog", "changelog.md",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "poetry.lock", "pipfile.lock", "composer.lock", "gemfile.lock",
}


def _is_code_file(path: str) -> bool:
    """Check if a file path looks like a code file (not an asset/image/binary)."""
    name = path.split("/")[-1].lower()
    if name in _NON_CODE_FILENAMES:
        return False
    dot_pos = name.rfind(".")
    if dot_pos > 0:
        ext = name[dot_pos:]
        if ext in _NON_CODE_EXTENSIONS:
            return False
    return True


class WikiGenerateRequest(BaseModel):
    repo_id: str
    component_path: str
    component_name: str | None = None


class WikiBatchRequest(BaseModel):
    components: list[dict]  # [{"path": "...", "name": "...", "repo_id": "..."}]


@router.get("/knowledge/wiki/suggestions")
def get_wiki_suggestions(
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    """Return suggested components for wiki generation (those without wikis yet)."""

    # Get existing wiki paths
    existing = db.execute(
        text("SELECT component_path FROM knowledge_wikis WHERE product_id = :product_id"),
        {"product_id": product.id},
    ).all()
    existing_paths = {row[0] for row in existing}

    suggestions = []
    seen_paths = set()

    # 1. Top files from code_chunks (grouped by file_path, sorted by chunk count)
    code_files = db.execute(text("""
        SELECT file_path, COUNT(*) as chunk_count, repo_name
        FROM code_chunks
        WHERE product_id = :product_id
        GROUP BY file_path, repo_name
        ORDER BY COUNT(*) DESC
        LIMIT 50
    """), {"product_id": product.id}).all()

    for row in code_files:
        path = row[0]
        if path in existing_paths or path in seen_paths or not _is_code_file(path):
            continue
        seen_paths.add(path)
        # Generate display name
        name = path.split("/")[-1]
        dot_pos = name.rfind(".")
        if dot_pos > 0:
            name = name[:dot_pos]
        display_name = name.replace("_", " ").replace("-", " ").title()
        suggestions.append({
            "path": path,
            "name": display_name,
            "repo_name": row[2],
            "source": "code",
            "chunk_count": row[1],
        })

    # 2. Component paths from knowledge_entries (file_paths field)
    knowledge_files = db.execute(text("""
        SELECT DISTINCT jsonb_array_elements_text(file_paths) AS fp
        FROM knowledge_entries
        WHERE product_id = :product_id AND file_paths IS NOT NULL
        LIMIT 100
    """), {"product_id": product.id}).all()

    for row in knowledge_files:
        path = row[0]
        if path in existing_paths or path in seen_paths or not _is_code_file(path):
            continue
        seen_paths.add(path)
        name = path.split("/")[-1]
        dot_pos = name.rfind(".")
        if dot_pos > 0:
            name = name[:dot_pos]
        display_name = name.replace("_", " ").replace("-", " ").title()
        suggestions.append({
            "path": path,
            "name": display_name,
            "repo_name": None,
            "source": "knowledge",
            "chunk_count": 0,
        })

    return suggestions


@router.post("/knowledge/wiki/generate")
def generate_wiki(
    body: WikiGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    background_tasks.add_task(
        _generate_wiki_bg, user.org_id, body.repo_id, body.component_path, body.component_name
    )
    return {"status": "generating", "component_path": body.component_path}


@router.post("/knowledge/wiki/generate-batch")
def generate_wiki_batch(
    body: WikiBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    """Generate wikis for multiple components at once."""
    if not body.components:
        raise HTTPException(status_code=400, detail="Nenhum componente selecionado")
    if len(body.components) > 20:
        raise HTTPException(status_code=400, detail="Maximo 20 componentes por vez")

    background_tasks.add_task(_generate_wiki_batch_bg, user.org_id, body.components)
    return {"status": "generating", "count": len(body.components)}


def _generate_wiki_bg(org_id: str, repo_id: str, component_path: str, component_name: str | None):
    db = SessionLocal()
    try:
        generator = WikiGenerator(db, org_id)
        generator.generate(repo_id, component_path, component_name)
        logger.info(f"Wiki generated for {component_path}")
    except Exception as e:
        logger.error(f"Wiki generation failed: {e}")
    finally:
        db.close()


def _generate_wiki_batch_bg(org_id: str, components: list[dict]):
    db = SessionLocal()
    try:
        generator = WikiGenerator(db, org_id)
        for comp in components:
            path = comp.get("path", "")
            name = comp.get("name")
            repo_id = comp.get("repo_id")
            try:
                generator.generate(repo_id=repo_id, component_path=path, component_name=name)
                logger.info(f"Wiki batch: generated for {path}")
            except Exception as e:
                logger.warning(f"Wiki batch: failed for {path}: {e}")
        logger.info(f"Wiki batch complete: {len(components)} components for org {org_id}")
    except Exception as e:
        logger.error(f"Wiki batch generation failed: {e}")
    finally:
        db.close()


@router.get("/knowledge/wikis")
def list_wikis(
    repo_id: str | None = Query(None),
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    query = "SELECT * FROM knowledge_wikis WHERE product_id = :product_id"
    params: dict = {"product_id": product.id}
    if repo_id:
        query += " AND repo_id = :repo_id"
        params["repo_id"] = repo_id
    query += " ORDER BY component_name"
    rows = db.execute(text(query), params).mappings().all()

    return [
        {
            "id": r["id"],
            "repo_id": r.get("repo_id"),
            "component_name": r["component_name"],
            "component_path": r["component_path"],
            "generation_version": r["generation_version"],
            "last_generated_at": str(r["last_generated_at"]) if r.get("last_generated_at") else None,
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


@router.delete("/knowledge/wiki/{wiki_id}")
def delete_wiki(wiki_id: str, db: Session = Depends(get_data_session), user: User = Depends(_get_user), product: Product = Depends(get_current_product)):
    result = db.execute(
        text("DELETE FROM knowledge_wikis WHERE id = :id AND product_id = :product_id"),
        {"id": wiki_id, "product_id": product.id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Wiki nao encontrada")
    return {"deleted": True}


@router.get("/knowledge/wiki/{wiki_id}")
def get_wiki(wiki_id: str, db: Session = Depends(get_data_session), user: User = Depends(_get_user), product: Product = Depends(get_current_product)):
    row = db.execute(
        text("SELECT * FROM knowledge_wikis WHERE id = :id AND product_id = :product_id"),
        {"id": wiki_id, "product_id": product.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Wiki nao encontrada")
    result = dict(row)
    for k in ("last_generated_at", "created_at", "updated_at"):
        if result.get(k):
            result[k] = str(result[k])
    return result


# ===== GitHub Sync =====

@router.post("/knowledge/sync/{repo_name:path}")
def sync_repository(
    repo_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
    product: Product = Depends(get_current_product),
):
    """Trigger extraction of PRs, commits, and issues from a GitHub repo."""
    # Build full repo name (owner/repo) from GitHub integration
    repo_full_name = repo_name
    if "/" not in repo_name:
        row = db.execute(
            text("SELECT github_login FROM github_integration WHERE org_id = :org_id AND is_active = true LIMIT 1"),
            {"org_id": user.org_id},
        ).mappings().first()
        if row:
            repo_full_name = f"{row['github_login']}/{repo_name}"
        else:
            raise HTTPException(status_code=400, detail="GitHub nao conectado. Configure em Configuracoes > Integracoes.")

    background_tasks.add_task(_sync_repo_bg, user.org_id, repo_full_name)
    return {"status": "syncing", "repo_name": repo_full_name}


def _sync_repo_bg(org_id: str, repo_full_name: str):
    db = SessionLocal()
    try:
        extractor = KnowledgeExtractor(db, org_id)
        result = extractor.sync_all(repo_full_name)
        logger.info(f"Knowledge sync complete for {repo_full_name}: {result}")
    except Exception as e:
        logger.error(f"Knowledge sync failed for {repo_full_name}: {e}")
    finally:
        db.close()


# ===== Stats =====

@router.get("/knowledge/stats")
def knowledge_stats(db: Session = Depends(get_data_session), user: User = Depends(_get_user), product: Product = Depends(get_current_product)):
    row = db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE source_type IN ('pr', 'commit')) as prs_commits,
            COUNT(*) FILTER (WHERE source_type = 'document') as documents,
            COUNT(*) FILTER (WHERE source_type = 'adr') as adrs,
            COUNT(*) FILTER (WHERE source_type = 'issue') as issues
        FROM knowledge_entries
        WHERE product_id = :product_id
    """), {"product_id": product.id}).mappings().first()

    wikis_count = db.execute(
        text("SELECT COUNT(*) FROM knowledge_wikis WHERE product_id = :product_id"),
        {"product_id": product.id},
    ).scalar()

    return {
        "total_entries": row["total"] if row else 0,
        "prs_commits": row["prs_commits"] if row else 0,
        "documents": row["documents"] if row else 0,
        "adrs": row["adrs"] if row else 0,
        "issues": row["issues"] if row else 0,
        "wikis": wikis_count or 0,
    }


# ===== Knowledge Settings =====


class KnowledgeSettingsPayload(BaseModel):
    auto_wiki: bool = False
    auto_sync: bool = False


@router.get("/knowledge/settings")
def get_knowledge_settings(db: Session = Depends(get_data_session), user: User = Depends(_get_user)):
    row = db.execute(
        text("SELECT settings FROM organizations WHERE id = :org_id"),
        {"org_id": user.org_id},
    ).mappings().first()
    org_settings = (row["settings"] or {}) if row else {}
    knowledge = org_settings.get("knowledge", {})
    return {
        "auto_wiki": knowledge.get("auto_wiki", False),
        "auto_sync": knowledge.get("auto_sync", False),
    }


@router.put("/knowledge/settings")
def update_knowledge_settings(
    payload: KnowledgeSettingsPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_data_session),
    user: User = Depends(_get_user),
):
    # Read previous settings
    row = db.execute(
        text("SELECT settings FROM organizations WHERE id = :org_id"),
        {"org_id": user.org_id},
    ).mappings().first()
    org_settings = dict(row["settings"] or {}) if row else {}

    org_settings["knowledge"] = {
        "auto_wiki": payload.auto_wiki,
        "auto_sync": payload.auto_sync,
    }
    db.execute(
        text("UPDATE organizations SET settings = :settings WHERE id = :org_id"),
        {"settings": json.dumps(org_settings), "org_id": user.org_id},
    )
    db.commit()

    # Trigger sync/wiki if enabled
    if payload.auto_sync or payload.auto_wiki:
        background_tasks.add_task(_initial_auto_run, user.org_id, payload.auto_sync)

    return org_settings["knowledge"]


def _initial_auto_run(org_id: str, do_sync: bool):
    """Run initial sync for all repos when auto features are first enabled.
    Wiki generation is now suggestion-based — admin must approve via UI."""
    db = SessionLocal()
    try:
        if not do_sync:
            logger.info(f"Auto run: sync not enabled for org {org_id}")
            return

        # Find all indexed repos for this org
        repos = db.execute(
            text("SELECT DISTINCT repo_name FROM code_chunks WHERE org_id = :org_id"),
            {"org_id": org_id},
        ).all()

        if not repos:
            logger.info(f"Auto run: no repos found for org {org_id}")
            return

        # Get GitHub login for full repo name
        gh_row = db.execute(
            text("SELECT github_login FROM github_integration WHERE org_id = :org_id AND is_active = true LIMIT 1"),
            {"org_id": org_id},
        ).mappings().first()
        gh_login = gh_row["github_login"] if gh_row else None

        if not gh_login:
            logger.info(f"Auto run: no GitHub login found for org {org_id}")
            return

        for repo_row in repos:
            repo_name = repo_row[0]
            full_name = f"{gh_login}/{repo_name}" if "/" not in repo_name else repo_name
            try:
                extractor = KnowledgeExtractor(db, org_id)
                result = extractor.sync_all(full_name)
                logger.info(f"Initial auto-sync for {full_name}: {result}")
            except Exception as e:
                logger.error(f"Initial auto-sync failed for {full_name}: {e}")

        logger.info(f"Auto run complete for org {org_id}: synced {len(repos)} repos")

    except Exception as e:
        logger.error(f"Initial auto run failed for org {org_id}: {e}")
    finally:
        db.close()
