import logging
import tempfile

from git import Repo
from sqlalchemy.orm import Session

from app.models.github_integration import GitHubIntegration

logger = logging.getLogger(__name__)


def _get_active_token(db: Session) -> str:
    """Busca o token ativo da tabela github_integration."""
    integration = (
        db.query(GitHubIntegration)
        .filter(GitHubIntegration.is_active.is_(True))
        .first()
    )
    if not integration:
        raise RuntimeError(
            "GitHub não conectado. Configure em Configurações > Integrações."
        )
    return integration.github_token


def clone_repository(repo_url: str, db: Session, target_dir: str | None = None) -> str:
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="memora_")

    if "github.com" in repo_url:
        token = _get_active_token(db)
        repo_url = repo_url.replace(
            "https://github.com",
            f"https://{token}@github.com",
        )

    logger.info(f"Clonando {repo_url} em {target_dir}")
    Repo.clone_from(repo_url, target_dir, depth=1)
    return target_dir


def pull_repository(repo_path: str) -> list[str]:
    repo = Repo(repo_path)
    origin = repo.remotes.origin

    fetch_info = origin.pull()
    changed_files = []
    for info in fetch_info:
        if info.flags & info.FAST_FORWARD:
            diff = repo.head.commit.diff(info.old_commit)
            changed_files.extend([d.a_path for d in diff if d.a_path.endswith(".py")])

    return changed_files
