"""Extrai conhecimento técnico de PRs, commits e issues do GitHub."""

import json
import logging
import uuid
from datetime import datetime

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder
from app.integrations import llm_router

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = (
    "Voce e um especialista em documentacao tecnica. "
    "Analise o conteudo abaixo e extraia o conhecimento tecnico relevante em portugues brasileiro. "
    "Foque em: decisoes de arquitetura, motivos de mudancas, problemas resolvidos e padroes estabelecidos."
)

EXTRACTION_USER_TEMPLATE = """Analise este {source_type} do GitHub e extraia:
1. Titulo descritivo (max 80 chars)
2. Resumo do que foi feito (2-3 paragrafos)
3. Tipo de decisao: arquitetura | dependencia | padrao | correcao | refatoracao
4. Componentes afetados (lista de modulos/arquivos principais)
5. Por que essa decisao foi tomada (se identificavel)

Responda apenas em JSON com as chaves: title, summary, decision_type, components, reasoning

Conteudo:
{content}"""

# Commits to skip (noise)
SKIP_PATTERNS = (
    "merge branch", "merge pull request", "fix typo", "update readme",
    "wip", "initial commit", "revert", "bump version",
)


def _github_headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _get_github_token(db: Session, org_id: str) -> str:
    row = db.execute(
        text("SELECT github_token FROM github_integration WHERE org_id = :org_id AND is_active = true LIMIT 1"),
        {"org_id": org_id},
    ).mappings().first()
    if not row:
        raise ValueError("GitHub nao conectado. Configure em Configuracoes > Integracoes.")
    return row["github_token"]


def _extract_with_llm(db: Session, org_id: str, source_type: str, content: str) -> dict:
    """Send content to LLM for extraction. Returns parsed JSON or fallback."""
    user_message = EXTRACTION_USER_TEMPLATE.format(source_type=source_type, content=content[:8000])

    try:
        result = llm_router.complete(
            db=db,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_message=user_message,
            org_id=org_id,
            max_tokens=1024,
        )
        return _parse_extraction_response(result["content"])
    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
        return {
            "title": content[:80],
            "summary": content[:500],
            "decision_type": "correcao",
            "components": [],
            "reasoning": "",
        }


def _parse_extraction_response(text_content: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    cleaned = text_content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "title": cleaned[:80],
            "summary": cleaned[:500],
            "decision_type": "correcao",
            "components": [],
            "reasoning": "",
        }

    return {
        "title": data.get("title", "")[:500],
        "summary": data.get("summary", ""),
        "decision_type": data.get("decision_type", "correcao"),
        "components": data.get("components", []),
        "reasoning": data.get("reasoning", ""),
    }


def _save_entry(
    db: Session,
    org_id: str,
    repo_id: str | None,
    source_type: str,
    source_id: str | None,
    source_url: str | None,
    title: str,
    content: str,
    summary: str,
    embedding: list[float] | None,
    file_paths: list[str] | None,
    components: list[str] | None,
    decision_type: str | None,
    source_date: datetime | None,
) -> str:
    entry_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO knowledge_entries
            (id, org_id, repo_id, source_type, source_id, source_url, title, content,
             summary, embedding, file_paths, components, decision_type, source_date)
        VALUES
            (:id, :org_id, :repo_id, :source_type, :source_id, :source_url, :title, :content,
             :summary, CAST(:embedding AS vector), :file_paths, :components, :decision_type, :source_date)
    """), {
        "id": entry_id,
        "org_id": org_id,
        "repo_id": repo_id,
        "source_type": source_type,
        "source_id": source_id,
        "source_url": source_url,
        "title": title,
        "content": content,
        "summary": summary,
        "embedding": str(embedding) if embedding else None,
        "file_paths": json.dumps(file_paths) if file_paths else None,
        "components": json.dumps(components) if components else None,
        "decision_type": decision_type,
        "source_date": source_date,
    })
    db.commit()
    return entry_id


def _already_extracted(db: Session, org_id: str, source_type: str, source_id: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM knowledge_entries WHERE org_id = :org_id AND source_type = :st AND source_id = :sid LIMIT 1"),
        {"org_id": org_id, "st": source_type, "sid": source_id},
    ).first()
    return row is not None


class KnowledgeExtractor:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id
        self._embedder = Embedder()

    def extract_prs(self, repo_full_name: str, repo_id: str | None = None, since: datetime | None = None) -> dict:
        """Extract knowledge from closed PRs."""
        token = _get_github_token(self._db, self._org_id)
        headers = _github_headers(token)
        extracted = 0
        skipped = 0

        params = {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 30}
        if since:
            params["since"] = since.isoformat()

        with httpx.Client(timeout=30) as client:
            resp = client.get(f"https://api.github.com/repos/{repo_full_name}/pulls", headers=headers, params=params)
            resp.raise_for_status()
            prs = resp.json()

            for pr in prs:
                pr_number = str(pr["number"])
                if _already_extracted(self._db, self._org_id, "pr", pr_number):
                    skipped += 1
                    continue

                # Build content for LLM
                pr_content = f"PR #{pr['number']}: {pr['title']}\n\n"
                pr_content += f"Autor: {pr['user']['login']}\n"
                pr_content += f"Labels: {', '.join(l['name'] for l in pr.get('labels', []))}\n"
                pr_content += f"Descricao: {pr.get('body', '') or 'Sem descricao'}\n\n"

                # Fetch files changed
                try:
                    files_resp = client.get(
                        f"https://api.github.com/repos/{repo_full_name}/pulls/{pr['number']}/files",
                        headers=headers,
                    )
                    files_resp.raise_for_status()
                    files = [f["filename"] for f in files_resp.json()[:20]]
                    pr_content += f"Arquivos modificados: {', '.join(files)}\n"
                except Exception:
                    files = []

                # Fetch review comments
                try:
                    comments_resp = client.get(
                        f"https://api.github.com/repos/{repo_full_name}/pulls/{pr['number']}/comments",
                        headers=headers, params={"per_page": 10},
                    )
                    comments_resp.raise_for_status()
                    for comment in comments_resp.json()[:5]:
                        pr_content += f"\nComentario de revisao ({comment['user']['login']}): {comment['body'][:300]}\n"
                except Exception:
                    pass

                # Extract with LLM
                extraction = _extract_with_llm(self._db, self._org_id, "Pull Request", pr_content)

                # Generate embedding
                embed_text = f"{extraction['title']}\n{extraction['summary']}"
                embedding = self._embedder.embed_text(embed_text)

                merged_at = pr.get("merged_at")
                source_date = datetime.fromisoformat(merged_at.replace("Z", "+00:00")) if merged_at else None

                _save_entry(
                    db=self._db,
                    org_id=self._org_id,
                    repo_id=repo_id,
                    source_type="pr",
                    source_id=pr_number,
                    source_url=pr.get("html_url"),
                    title=extraction["title"],
                    content=pr_content,
                    summary=extraction["summary"],
                    embedding=embedding,
                    file_paths=files or None,
                    components=extraction.get("components") or None,
                    decision_type=extraction.get("decision_type"),
                    source_date=source_date,
                )
                extracted += 1

        return {"extracted": extracted, "skipped": skipped}

    def extract_commits(self, repo_full_name: str, repo_id: str | None = None, since: datetime | None = None) -> dict:
        """Extract knowledge from meaningful commits."""
        token = _get_github_token(self._db, self._org_id)
        headers = _github_headers(token)
        extracted = 0
        skipped = 0

        params = {"per_page": 50}
        if since:
            params["since"] = since.isoformat()

        with httpx.Client(timeout=30) as client:
            resp = client.get(f"https://api.github.com/repos/{repo_full_name}/commits", headers=headers, params=params)
            resp.raise_for_status()
            commits = resp.json()

            for commit in commits:
                sha = commit["sha"][:7]
                message = commit["commit"]["message"]

                # Skip noise
                if any(p in message.lower() for p in SKIP_PATTERNS):
                    skipped += 1
                    continue

                if _already_extracted(self._db, self._org_id, "commit", sha):
                    skipped += 1
                    continue

                # Build content
                commit_content = f"Commit {sha}: {message}\n"
                commit_content += f"Autor: {commit['commit']['author']['name']}\n"

                # Fetch commit detail for file list
                try:
                    detail = client.get(f"https://api.github.com/repos/{repo_full_name}/commits/{commit['sha']}", headers=headers)
                    detail.raise_for_status()
                    detail_data = detail.json()
                    files = [f["filename"] for f in detail_data.get("files", [])[:20]]
                    commit_content += f"Arquivos: {', '.join(files)}\n"
                except Exception:
                    files = []

                extraction = _extract_with_llm(self._db, self._org_id, "Commit", commit_content)

                embed_text = f"{extraction['title']}\n{extraction['summary']}"
                embedding = self._embedder.embed_text(embed_text)

                commit_date_str = commit["commit"]["author"]["date"]
                source_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00")) if commit_date_str else None

                _save_entry(
                    db=self._db,
                    org_id=self._org_id,
                    repo_id=repo_id,
                    source_type="commit",
                    source_id=sha,
                    source_url=commit.get("html_url"),
                    title=extraction["title"],
                    content=commit_content,
                    summary=extraction["summary"],
                    embedding=embedding,
                    file_paths=files or None,
                    components=extraction.get("components") or None,
                    decision_type=extraction.get("decision_type"),
                    source_date=source_date,
                )
                extracted += 1

        return {"extracted": extracted, "skipped": skipped}

    def extract_issues(self, repo_full_name: str, repo_id: str | None = None, since: datetime | None = None) -> dict:
        """Extract knowledge from closed issues."""
        token = _get_github_token(self._db, self._org_id)
        headers = _github_headers(token)
        extracted = 0
        skipped = 0

        params = {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 30}
        if since:
            params["since"] = since.isoformat()

        with httpx.Client(timeout=30) as client:
            resp = client.get(f"https://api.github.com/repos/{repo_full_name}/issues", headers=headers, params=params)
            resp.raise_for_status()
            issues = resp.json()

            for issue in issues:
                # Skip PRs (GitHub API returns PRs as issues too)
                if "pull_request" in issue:
                    continue

                issue_number = str(issue["number"])
                if _already_extracted(self._db, self._org_id, "issue", issue_number):
                    skipped += 1
                    continue

                issue_content = f"Issue #{issue['number']}: {issue['title']}\n\n"
                issue_content += f"Autor: {issue['user']['login']}\n"
                issue_content += f"Labels: {', '.join(l['name'] for l in issue.get('labels', []))}\n"
                issue_content += f"Descricao: {issue.get('body', '') or 'Sem descricao'}\n\n"

                # Fetch comments
                try:
                    comments_resp = client.get(
                        f"https://api.github.com/repos/{repo_full_name}/issues/{issue['number']}/comments",
                        headers=headers, params={"per_page": 10},
                    )
                    comments_resp.raise_for_status()
                    for comment in comments_resp.json()[:5]:
                        issue_content += f"\nComentario ({comment['user']['login']}): {comment['body'][:300]}\n"
                except Exception:
                    pass

                extraction = _extract_with_llm(self._db, self._org_id, "Issue", issue_content)

                embed_text = f"{extraction['title']}\n{extraction['summary']}"
                embedding = self._embedder.embed_text(embed_text)

                closed_at = issue.get("closed_at")
                source_date = datetime.fromisoformat(closed_at.replace("Z", "+00:00")) if closed_at else None

                _save_entry(
                    db=self._db,
                    org_id=self._org_id,
                    repo_id=repo_id,
                    source_type="issue",
                    source_id=issue_number,
                    source_url=issue.get("html_url"),
                    title=extraction["title"],
                    content=issue_content,
                    summary=extraction["summary"],
                    embedding=embedding,
                    file_paths=None,
                    components=extraction.get("components") or None,
                    decision_type=extraction.get("decision_type"),
                    source_date=source_date,
                )
                extracted += 1

        return {"extracted": extracted, "skipped": skipped}

    def sync_all(self, repo_full_name: str, repo_id: str | None = None, since: datetime | None = None) -> dict:
        """Run all extractors and aggregate results."""
        pr_result = self.extract_prs(repo_full_name, repo_id, since)
        commit_result = self.extract_commits(repo_full_name, repo_id, since)
        issue_result = self.extract_issues(repo_full_name, repo_id, since)

        return {
            "extracted": pr_result["extracted"] + commit_result["extracted"] + issue_result["extracted"],
            "skipped": pr_result["skipped"] + commit_result["skipped"] + issue_result["skipped"],
            "details": {
                "prs": pr_result,
                "commits": commit_result,
                "issues": issue_result,
            },
        }
