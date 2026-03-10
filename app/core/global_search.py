"""Busca global que atravessa todos os modulos do Memora."""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder

logger = logging.getLogger(__name__)

RRF_K = 60


def _truncate(s: str | None, length: int = 150) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").strip()
    return s[:length] + "..." if len(s) > length else s


def _search_conversations(
    db: Session, query: str, org_id: str, product_id: str, limit: int,
) -> list[dict]:
    """Busca em conversas + mensagens."""
    rows = db.execute(
        text("""
            SELECT m.id, c.title, m.content, m.created_at, c.repo_name, c.id AS conv_id
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.org_id = :org_id
              AND c.product_id = :product_id
              AND m.role = 'user'
              AND (
                  to_tsvector('portuguese', m.content) @@ plainto_tsquery('portuguese', :query)
                  OR to_tsvector('portuguese', COALESCE(c.title, '')) @@ plainto_tsquery('portuguese', :query)
              )
            ORDER BY m.created_at DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "product_id": product_id, "query": query, "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": r.title or _truncate(r.content, 60),
            "preview": _truncate(r.content),
            "source": "conversations",
            "source_label": "Conversas",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/chat/{r.repo_name}?conversation={r.conv_id}",
        }
        for r in rows
    ]


def _search_business_rules(
    db: Session, query: str, embedding: list[float],
    org_id: str, product_id: str, limit: int,
) -> list[dict]:
    """Busca em regras de negocio (hibrida)."""
    rows = db.execute(
        text("""
            SELECT id, title, description, plain_english, rule_type, created_at,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS sem_score,
                   ts_rank(
                       setweight(to_tsvector('portuguese', title), 'A') ||
                       setweight(to_tsvector('portuguese', COALESCE(description, '')), 'B'),
                       plainto_tsquery('portuguese', :query)
                   ) AS txt_score
            FROM business_rules
            WHERE org_id = :org_id AND product_id = :product_id AND is_active = true
              AND (
                  embedding IS NOT NULL
                  OR to_tsvector('portuguese', COALESCE(title, '') || ' ' || COALESCE(description, ''))
                     @@ plainto_tsquery('portuguese', :query)
              )
            ORDER BY GREATEST(
                1 - (embedding <=> CAST(:embedding AS vector)),
                ts_rank(
                    setweight(to_tsvector('portuguese', title), 'A') ||
                    setweight(to_tsvector('portuguese', COALESCE(description, '')), 'B'),
                    plainto_tsquery('portuguese', :query)
                )
            ) DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "product_id": product_id, "query": query,
         "embedding": str(embedding), "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": r.title,
            "preview": _truncate(r.plain_english or r.description),
            "source": "business_rules",
            "source_label": "Regras de Negocio",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/dashboard/rules?highlight={r.id}",
        }
        for r in rows
    ]


def _search_knowledge_entries(
    db: Session, query: str, embedding: list[float],
    org_id: str, product_id: str, limit: int,
) -> list[dict]:
    """Busca em knowledge_entries (hibrida)."""
    rows = db.execute(
        text("""
            SELECT id, title, summary, content, source_type, created_at
            FROM knowledge_entries
            WHERE org_id = :org_id AND product_id = :product_id
              AND (
                  embedding IS NOT NULL
                  OR to_tsvector('portuguese', COALESCE(title, '') || ' ' || COALESCE(content, ''))
                     @@ plainto_tsquery('portuguese', :query)
              )
            ORDER BY GREATEST(
                1 - (embedding <=> CAST(:embedding AS vector)),
                ts_rank(
                    setweight(to_tsvector('portuguese', COALESCE(title, '')), 'A') ||
                    setweight(to_tsvector('portuguese', COALESCE(content, '')), 'B'),
                    plainto_tsquery('portuguese', :query)
                )
            ) DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "product_id": product_id, "query": query,
         "embedding": str(embedding), "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": r.title,
            "preview": _truncate(r.summary or r.content),
            "source": "knowledge_entries",
            "source_label": "Memoria Tecnica",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/dashboard/memory?tab=timeline&highlight={r.id}",
        }
        for r in rows
    ]


def _search_repo_docs(
    db: Session, query: str, org_id: str, limit: int,
) -> list[dict]:
    """Busca em repo_docs."""
    rows = db.execute(
        text("""
            SELECT id, repo_name, doc_type, content, created_at
            FROM repo_docs
            WHERE org_id = :org_id
              AND to_tsvector('portuguese', content) @@ plainto_tsquery('portuguese', :query)
            ORDER BY ts_rank(to_tsvector('portuguese', content), plainto_tsquery('portuguese', :query)) DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "query": query, "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": f"{r.repo_name} — {r.doc_type}",
            "preview": _truncate(r.content),
            "source": "repo_docs",
            "source_label": "Documentacao",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/dashboard/docs?repo={r.repo_name}",
        }
        for r in rows
    ]


def _search_review_findings(
    db: Session, query: str, org_id: str, limit: int,
) -> list[dict]:
    """Busca em review_findings."""
    rows = db.execute(
        text("""
            SELECT rf.id, rf.title, rf.description, rf.severity, rf.category,
                   rf.review_id, rf.created_at
            FROM review_findings rf
            WHERE rf.org_id = :org_id
              AND (
                  to_tsvector('portuguese', COALESCE(rf.title, '') || ' ' || COALESCE(rf.description, ''))
                  @@ plainto_tsquery('portuguese', :query)
              )
            ORDER BY rf.created_at DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "query": query, "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": f"[{r.severity}] {r.title}",
            "preview": _truncate(r.description),
            "source": "review_findings",
            "source_label": "Revisao de Codigo",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/dashboard/reviews/{r.review_id}",
        }
        for r in rows
    ]


def _search_security_findings(
    db: Session, query: str, org_id: str, limit: int,
) -> list[dict]:
    """Busca em security_findings."""
    rows = db.execute(
        text("""
            SELECT sf.id, sf.title, sf.description, sf.severity, sf.scan_id, sf.created_at
            FROM security_findings sf
            WHERE sf.org_id = :org_id
              AND (
                  to_tsvector('portuguese', COALESCE(sf.title, '') || ' ' || COALESCE(sf.description, ''))
                  @@ plainto_tsquery('portuguese', :query)
              )
            ORDER BY sf.created_at DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "query": query, "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": f"[{r.severity}] {r.title}",
            "preview": _truncate(r.description),
            "source": "security_findings",
            "source_label": "Seguranca",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/dashboard/security?scan={r.scan_id}&finding={r.id}",
        }
        for r in rows
    ]


def _search_error_alerts(
    db: Session, query: str, org_id: str, limit: int,
) -> list[dict]:
    """Busca em error_alerts."""
    rows = db.execute(
        text("""
            SELECT ea.id, ea.title, ea.explanation, ea.severity, ea.project_id, ea.created_at
            FROM error_alerts ea
            WHERE ea.org_id = :org_id
              AND (
                  to_tsvector('portuguese', COALESCE(ea.title, '') || ' ' || COALESCE(ea.explanation, ''))
                  @@ plainto_tsquery('portuguese', :query)
              )
            ORDER BY ea.created_at DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "query": query, "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": r.title,
            "preview": _truncate(r.explanation),
            "source": "error_alerts",
            "source_label": "Alertas",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/dashboard/monitor/{r.project_id}?alert={r.id}",
        }
        for r in rows
    ]


def _search_knowledge_wikis(
    db: Session, query: str, org_id: str, limit: int,
) -> list[dict]:
    """Busca em knowledge_wikis."""
    rows = db.execute(
        text("""
            SELECT id, component_name, component_path, content, created_at
            FROM knowledge_wikis
            WHERE org_id = :org_id
              AND to_tsvector('portuguese', COALESCE(component_name, '') || ' ' || content)
                  @@ plainto_tsquery('portuguese', :query)
            ORDER BY ts_rank(
                to_tsvector('portuguese', COALESCE(component_name, '') || ' ' || content),
                plainto_tsquery('portuguese', :query)
            ) DESC
            LIMIT :limit
        """),
        {"org_id": org_id, "query": query, "limit": limit},
    ).fetchall()

    return [
        {
            "id": str(r.id),
            "title": r.component_name,
            "preview": _truncate(r.content),
            "source": "knowledge_wikis",
            "source_label": "Wikis",
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "url": f"/dashboard/memory?tab=wiki&component={r.component_path}",
        }
        for r in rows
    ]


def global_search(
    db: Session,
    query: str,
    org_id: str,
    product_id: str,
    user_role: str,
    limit: int = 5,
) -> dict:
    """Executa busca global em todas as fontes.

    Retorna dict com results agrupados por fonte, total e query.
    """
    # Gerar embedding uma vez para fontes que suportam busca semantica
    embedder = Embedder()
    embedding = embedder.embed_text(query)

    results: dict[str, list[dict]] = {}
    total = 0

    # Definir fontes e suas funcoes de busca
    searches: list[tuple[str, callable]] = [
        ("conversations", lambda: _search_conversations(db, query, org_id, product_id, limit)),
        ("business_rules", lambda: _search_business_rules(db, query, embedding, org_id, product_id, limit)),
        ("knowledge_entries", lambda: _search_knowledge_entries(db, query, embedding, org_id, product_id, limit)),
        ("repo_docs", lambda: _search_repo_docs(db, query, org_id, limit)),
        ("review_findings", lambda: _search_review_findings(db, query, org_id, limit)),
        ("error_alerts", lambda: _search_error_alerts(db, query, org_id, limit)),
        ("knowledge_wikis", lambda: _search_knowledge_wikis(db, query, org_id, limit)),
    ]

    # Security findings: apenas para admin e dev
    if user_role in ("admin", "dev"):
        searches.append(
            ("security_findings", lambda: _search_security_findings(db, query, org_id, limit)),
        )

    for source_name, search_fn in searches:
        try:
            items = search_fn()
            if items:
                results[source_name] = items
                total += len(items)
        except Exception as exc:
            logger.warning("Busca global falhou para %s: %s", source_name, exc)

    return {
        "results": results,
        "total": total,
        "query": query,
    }
