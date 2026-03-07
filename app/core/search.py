import logging
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder

logger = logging.getLogger(__name__)

RRF_K = 60


class HybridSearch:
    def __init__(self, db: Session):
        self._db = db
        self._embedder = Embedder()

    def semantic_search(self, query: str, repo_name: str, top_k: int = 10, org_id: str | None = None) -> list[dict]:
        query_embedding = self._embedder.embed_text(query)

        where = "WHERE repo_name = :repo_name"
        params: dict = {"embedding": str(query_embedding), "repo_name": repo_name, "top_k": top_k}
        if org_id:
            where += " AND org_id = :org_id"
            params["org_id"] = org_id

        sql = text(f"""
            SELECT id, file_path, chunk_name, chunk_type, content,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS score
            FROM code_chunks
            {where}
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        rows = self._db.execute(sql, params).fetchall()

        return [
            {
                "chunk_id": str(r.id),
                "file_path": r.file_path,
                "chunk_name": r.chunk_name,
                "chunk_type": r.chunk_type,
                "content": r.content,
                "score": float(r.score),
            }
            for r in rows
        ]

    def keyword_search(self, query: str, repo_name: str, top_k: int = 10, org_id: str | None = None) -> list[dict]:
        org_filter = "AND org_id = :org_id" if org_id else ""
        params: dict = {"query": query, "repo_name": repo_name, "top_k": top_k}
        if org_id:
            params["org_id"] = org_id

        sql = text(f"""
            SELECT id, file_path, chunk_name, chunk_type, content,
                   ts_rank(
                       setweight(to_tsvector('portuguese', chunk_name), 'A') ||
                       setweight(to_tsvector('portuguese', content), 'B'),
                       plainto_tsquery('portuguese', :query)
                   ) AS score
            FROM code_chunks
            WHERE repo_name = :repo_name
              {org_filter}
              AND (
                  to_tsvector('portuguese', content) @@ plainto_tsquery('portuguese', :query)
                  OR to_tsvector('portuguese', chunk_name) @@ plainto_tsquery('portuguese', :query)
              )
            ORDER BY score DESC
            LIMIT :top_k
        """)

        rows = self._db.execute(sql, params).fetchall()

        return [
            {
                "chunk_id": str(r.id),
                "file_path": r.file_path,
                "chunk_name": r.chunk_name,
                "chunk_type": r.chunk_type,
                "content": r.content,
                "score": float(r.score),
            }
            for r in rows
        ]

    def search(self, query: str, repo_name: str, top_k: int = 5, org_id: str | None = None) -> list[dict]:
        semantic_results = self.semantic_search(query, repo_name, top_k=top_k * 3, org_id=org_id)
        keyword_results = self.keyword_search(query, repo_name, top_k=top_k * 3, org_id=org_id)

        rrf_scores: dict[str, float] = defaultdict(float)
        chunk_data: dict[str, dict] = {}

        for rank, result in enumerate(semantic_results):
            cid = result["chunk_id"]
            rrf_scores[cid] += 1.0 / (RRF_K + rank + 1)
            chunk_data[cid] = result

        for rank, result in enumerate(keyword_results):
            cid = result["chunk_id"]
            rrf_scores[cid] += 1.0 / (RRF_K + rank + 1)
            if cid not in chunk_data:
                chunk_data[cid] = result

        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        results = []
        for cid in sorted_ids[:top_k]:
            entry = chunk_data[cid].copy()
            entry["rrf_score"] = round(rrf_scores[cid], 6)
            results.append(entry)

        logger.info(
            f"HybridSearch: query='{query[:50]}' repo={repo_name} "
            f"semantic={len(semantic_results)} keyword={len(keyword_results)} "
            f"final={len(results)}"
        )

        return results


# Função de conveniência mantida para compatibilidade com assistant.py
def search_chunks(
    db: Session,
    query: str,
    repo_name: str,
    max_results: int = 5,
    org_id: str | None = None,
) -> list[dict]:
    searcher = HybridSearch(db)
    return searcher.search(query, repo_name, top_k=max_results, org_id=org_id)
