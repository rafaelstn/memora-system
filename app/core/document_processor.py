"""Processa documentos uploaded (PDF, DOCX, MD, TXT) e extrai conhecimento."""

import json
import logging
import os
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder
from app.integrations import llm_router

logger = logging.getLogger(__name__)

DOCUMENT_SYSTEM_PROMPT = (
    "Voce e um especialista em documentacao tecnica. "
    "Analise o documento abaixo e gere um titulo descritivo e um resumo tecnico em portugues brasileiro."
)

DOCUMENT_USER_TEMPLATE = """Analise este documento e extraia:
1. Titulo descritivo (max 80 chars)
2. Resumo tecnico (2-3 paragrafos, em portugues)

Responda apenas em JSON com as chaves: title, summary

Conteudo do documento ({filename}):
{content}"""

ALLOWED_EXTENSIONS = {"pdf", "docx", "md", "txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Local upload directory (fallback when Supabase Storage is not configured)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "knowledge-docs")


def _extract_text_pdf(file_path: str) -> str:
    """Extract text from PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    parts = []
    for page in reader.pages:
        text_content = page.extract_text()
        if text_content:
            parts.append(text_content)
    return "\n\n".join(parts)


def _extract_text_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    import docx
    doc = docx.Document(file_path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_text_plain(file_path: str) -> str:
    """Extract text from MD or TXT files."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text(file_path: str, file_type: str) -> str:
    """Extract text from a file based on its type."""
    if file_type == "pdf":
        return _extract_text_pdf(file_path)
    elif file_type == "docx":
        return _extract_text_docx(file_path)
    elif file_type in ("md", "txt"):
        return _extract_text_plain(file_path)
    else:
        raise ValueError(f"Tipo de arquivo nao suportado: {file_type}")


def get_upload_path(org_id: str, filename: str) -> str:
    """Get the storage path for a file."""
    org_dir = os.path.join(UPLOAD_DIR, org_id)
    os.makedirs(org_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    return os.path.join(org_dir, safe_name)


class DocumentProcessor:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id
        self._embedder = Embedder()

    def process(self, document_id: str) -> str | None:
        """Process a document: extract text, generate summary, create knowledge entry."""
        doc = self._db.execute(
            text("SELECT * FROM knowledge_documents WHERE id = :id AND org_id = :org_id"),
            {"id": document_id, "org_id": self._org_id},
        ).mappings().first()

        if not doc:
            logger.error(f"Document {document_id} not found")
            return None

        if doc["processed"]:
            logger.info(f"Document {document_id} already processed")
            return doc.get("entry_id")

        try:
            # Extract text
            full_text = extract_text(doc["storage_path"], doc["file_type"])
            if not full_text.strip():
                logger.warning(f"Document {document_id} has no extractable text")
                return None

            # Truncate for LLM (keep first ~6000 chars for summary)
            truncated_text = full_text[:6000]

            # LLM extraction
            extraction = self._extract_with_llm(doc["filename"], truncated_text)

            # Generate embedding from title + summary
            embed_text = f"{extraction['title']}\n{extraction['summary']}"
            embedding = self._embedder.embed_text(embed_text)

            # Create knowledge entry
            entry_id = str(uuid.uuid4())
            self._db.execute(text("""
                INSERT INTO knowledge_entries
                    (id, org_id, repo_id, source_type, title, content, summary, embedding, created_by)
                VALUES
                    (:id, :org_id, :repo_id, 'document', :title, :content, :summary,
                     CAST(:embedding AS vector), :created_by)
            """), {
                "id": entry_id,
                "org_id": self._org_id,
                "repo_id": doc.get("repo_id"),
                "title": extraction["title"],
                "content": full_text[:50000],  # cap at 50k chars
                "summary": extraction["summary"],
                "embedding": str(embedding),
                "created_by": doc["uploaded_by"],
            })

            # Update document as processed
            self._db.execute(
                text("UPDATE knowledge_documents SET processed = true, entry_id = :entry_id WHERE id = :id"),
                {"entry_id": entry_id, "id": document_id},
            )
            self._db.commit()

            logger.info(f"Document {document_id} processed successfully -> entry {entry_id}")
            return entry_id

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            self._db.rollback()
            return None

    def _extract_with_llm(self, filename: str, content: str) -> dict:
        """Use LLM to generate title and summary for document."""
        user_message = DOCUMENT_USER_TEMPLATE.format(filename=filename, content=content)

        try:
            result = llm_router.complete(
                db=self._db,
                system_prompt=DOCUMENT_SYSTEM_PROMPT,
                user_message=user_message,
                org_id=self._org_id,
                max_tokens=1024,
            )
            return self._parse_response(result["content"], filename)
        except Exception as e:
            logger.warning(f"LLM extraction failed for document: {e}")
            return {
                "title": filename,
                "summary": content[:500],
            }

    def _parse_response(self, text_content: str, fallback_title: str) -> dict:
        cleaned = text_content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
            return {
                "title": data.get("title", fallback_title)[:500],
                "summary": data.get("summary", ""),
            }
        except json.JSONDecodeError:
            return {
                "title": fallback_title,
                "summary": cleaned[:500],
            }
