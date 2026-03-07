"""Cria tabelas repo_docs e onboarding_progress para o modulo de Documentacao Automatica."""

from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # repo_docs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS repo_docs (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                repo_name VARCHAR(255) NOT NULL,
                doc_type VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                content_hash VARCHAR(64),
                generated_at TIMESTAMP DEFAULT now(),
                generation_trigger VARCHAR(20) NOT NULL DEFAULT 'manual',
                pushed_to_github BOOLEAN NOT NULL DEFAULT false,
                pushed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))

        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_repo_docs_org ON repo_docs(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_repo_docs_repo ON repo_docs(repo_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_repo_docs_type ON repo_docs(doc_type)"))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_repo_docs_org_repo_type
            ON repo_docs(org_id, repo_name, doc_type)
        """))

        # onboarding_progress
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_progress (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                repo_name VARCHAR(255) NOT NULL,
                guide_id VARCHAR(36) NOT NULL REFERENCES repo_docs(id),
                steps_total INTEGER NOT NULL DEFAULT 0,
                steps_completed INTEGER NOT NULL DEFAULT 0,
                completed_steps JSONB NOT NULL DEFAULT '[]',
                started_at TIMESTAMP DEFAULT now(),
                completed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT now()
            )
        """))

        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_onboarding_org ON onboarding_progress(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_onboarding_user ON onboarding_progress(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_onboarding_repo ON onboarding_progress(repo_name)"))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_onboarding_user_repo
            ON onboarding_progress(user_id, repo_name)
        """))

    print("Tabelas repo_docs e onboarding_progress criadas com sucesso.")


if __name__ == "__main__":
    migrate()
