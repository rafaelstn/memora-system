import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.chunker import chunk_file, chunk_file_generic
from app.core.embedder import generate_embeddings_batched
from app.models.chunk import CodeChunk

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".java", ".go", ".rs", ".rb", ".php",
    ".css", ".scss", ".html", ".vue", ".svelte",
    ".sql", ".sh", ".yaml", ".yml", ".toml",
    ".md", ".json", ".env.example",
}

SKIP_DIRS = {".venv", "node_modules", "__pycache__", ".git", ".next", "dist", "build", ".tox"}


def _find_code_files(repo_path: str) -> list[Path]:
    root = Path(repo_path)
    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(skip in p.parts for skip in SKIP_DIRS):
            continue
        if p.suffix in SUPPORTED_EXTENSIONS:
            files.append(p)
    return sorted(files)


def _find_python_files(repo_path: str) -> list[Path]:
    root = Path(repo_path)
    return sorted(
        p for p in root.rglob("*.py")
        if ".venv" not in p.parts
        and "node_modules" not in p.parts
        and "__pycache__" not in p.parts
        and ".git" not in p.parts
    )


def _clear_repo_chunks(db: Session, repo_name: str, org_id: str, product_id: str | None = None) -> int:
    if product_id:
        result = db.execute(
            text("DELETE FROM code_chunks WHERE repo_name = :repo_name AND product_id = :product_id"),
            {"repo_name": repo_name, "product_id": product_id},
        )
    else:
        result = db.execute(
            text("DELETE FROM code_chunks WHERE repo_name = :repo_name AND org_id = :org_id"),
            {"repo_name": repo_name, "org_id": org_id},
        )
    db.commit()
    return result.rowcount


def ingest_repository(
    db: Session,
    repo_path: str,
    repo_name: str | None = None,
    org_id: str | None = None,
    product_id: str | None = None,
    on_progress=None,
) -> dict:
    """
    on_progress(stage, percent, detail) — callback opcional para reportar progresso.
    Stages: scanning, chunking, embedding, saving, done
    """
    root = Path(repo_path)
    if repo_name is None:
        repo_name = root.name

    def _progress(stage: str, percent: int, detail: str = ""):
        if on_progress:
            on_progress(stage, percent, detail)

    logger.info(f"Iniciando ingestão: {repo_name} ({repo_path}) org_id={org_id}")
    _progress("scanning", 5, "Limpando chunks anteriores...")

    deleted = _clear_repo_chunks(db, repo_name, org_id=org_id, product_id=product_id)
    if deleted:
        logger.info(f"Removidos {deleted} chunks anteriores de {repo_name}")

    _progress("scanning", 10, "Escaneando arquivos...")
    code_files = _find_code_files(repo_path)
    total_files = len(code_files)
    logger.info(f"Encontrados {total_files} arquivos de código")
    _progress("scanning", 15, f"{total_files} arquivos encontrados")

    all_chunks = []
    for idx, code_file in enumerate(code_files):
        try:
            rel_path = str(code_file.relative_to(root))
            if code_file.suffix == ".py":
                file_chunks = chunk_file(file_path=str(code_file))
            else:
                file_chunks = chunk_file_generic(file_path=str(code_file))
            for chunk in file_chunks:
                chunk["file_path"] = rel_path
            all_chunks.extend(file_chunks)
        except Exception as e:
            logger.error(f"Erro ao processar {code_file}: {e}")

        # Chunking progress: 15% → 50%
        pct = 15 + int(35 * (idx + 1) / max(total_files, 1))
        _progress("chunking", pct, f"Processando {idx + 1}/{total_files} arquivos")

    logger.info(f"Total de chunks extraídos: {len(all_chunks)}")

    if not all_chunks:
        _progress("done", 100, "Nenhum chunk criado")
        return {"repo_name": repo_name, "files_processed": total_files, "chunks_created": 0}

    # Embedding progress: 50% → 90%
    contents = [c["content"] for c in all_chunks]
    batch_size = 100  # matches embedder default
    total_batches = (len(contents) + batch_size - 1) // batch_size
    _progress("embedding", 50, f"Gerando embeddings (0/{total_batches} batches)...")
    embeddings = generate_embeddings_batched(
        contents,
        on_batch_done=lambda batch_num, total: _progress(
            "embedding",
            50 + int(40 * batch_num / max(total, 1)),
            f"Embeddings {batch_num}/{total} batches",
        ),
    )

    _progress("saving", 92, "Salvando no banco...")
    records = []
    for chunk, embedding in zip(all_chunks, embeddings):
        record = CodeChunk(
            repo_name=repo_name,
            file_path=chunk["file_path"],
            chunk_type=chunk["chunk_type"],
            chunk_name=chunk["chunk_name"],
            content=chunk["content"],
            embedding=embedding,
            metadata_={
                "start_line": chunk.get("start_line"),
                "end_line": chunk.get("end_line"),
                "docstring": chunk.get("docstring"),
            },
        )
        if org_id:
            record.org_id = org_id
        if product_id:
            record.product_id = product_id
        records.append(record)

    db.add_all(records)
    db.commit()

    logger.info(f"Ingestão concluída: {total_files} arquivos, {len(records)} chunks salvos")
    _progress("done", 100, f"{len(records)} chunks criados")

    return {
        "repo_name": repo_name,
        "files_processed": total_files,
        "chunks_created": len(records),
    }


def delete_chunks_by_file(db: Session, repo_name: str, file_path: str, org_id: str) -> int:
    result = db.execute(
        text("DELETE FROM code_chunks WHERE repo_name = :repo_name AND file_path = :file_path AND org_id = :org_id"),
        {"repo_name": repo_name, "file_path": file_path, "org_id": org_id},
    )
    db.commit()
    logger.info(f"Removidos {result.rowcount} chunks de {repo_name}:{file_path}")
    return result.rowcount


def reindex_files(
    db: Session,
    repo_name: str,
    repo_path: str,
    file_paths: list[str],
    org_id: str = "",
    product_id: str | None = None,
) -> dict:
    root = Path(repo_path)
    deleted_total = 0
    all_chunks = []

    for rel_path in file_paths:
        deleted_total += delete_chunks_by_file(db, repo_name, rel_path, org_id=org_id)

        abs_path = root / rel_path
        if not abs_path.exists():
            logger.info(f"Arquivo não existe (removido?): {rel_path}")
            continue

        try:
            file_chunks = chunk_file(file_path=str(abs_path))
            for chunk in file_chunks:
                chunk["file_path"] = rel_path
            all_chunks.extend(file_chunks)
        except Exception as e:
            logger.error(f"Erro ao processar {rel_path}: {e}")

    if not all_chunks:
        return {
            "repo_name": repo_name,
            "files_processed": len(file_paths),
            "chunks_deleted": deleted_total,
            "chunks_created": 0,
        }

    contents = [c["content"] for c in all_chunks]
    embeddings = generate_embeddings_batched(contents)

    records = []
    for chunk, embedding in zip(all_chunks, embeddings):
        record = CodeChunk(
            repo_name=repo_name,
            file_path=chunk["file_path"],
            chunk_type=chunk["chunk_type"],
            chunk_name=chunk["chunk_name"],
            content=chunk["content"],
            embedding=embedding,
            metadata_={
                "start_line": chunk.get("start_line"),
                "end_line": chunk.get("end_line"),
                "docstring": chunk.get("docstring"),
            },
        )
        if org_id:
            record.org_id = org_id
        if product_id:
            record.product_id = product_id
        records.append(record)

    db.add_all(records)
    db.commit()

    logger.info(
        f"Re-indexação incremental: {len(file_paths)} arquivos, "
        f"{deleted_total} chunks removidos, {len(records)} chunks criados"
    )

    return {
        "repo_name": repo_name,
        "files_processed": len(file_paths),
        "chunks_deleted": deleted_total,
        "chunks_created": len(records),
    }
