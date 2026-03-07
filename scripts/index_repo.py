"""
Indexação manual de repositório.
Uso: python scripts/index_repo.py <caminho-do-repo> [nome-do-repo]
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.core.ingestor import ingest_repository  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/index_repo.py <caminho-do-repo> [nome-do-repo]")
        sys.exit(1)

    repo_path = sys.argv[1]
    repo_name = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(repo_path).is_dir():
        print(f"Diretório não encontrado: {repo_path}")
        sys.exit(1)

    db = SessionLocal()
    try:
        result = ingest_repository(db=db, repo_path=repo_path, repo_name=repo_name)
        print(f"\nResultado:")
        print(f"  Repositório: {result['repo_name']}")
        print(f"  Arquivos processados: {result['files_processed']}")
        print(f"  Chunks criados: {result['chunks_created']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
