"""Migration: adiciona tabelas do Modulo 4 — Revisao de Codigo."""
from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # 1. code_reviews
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS code_reviews (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                repo_id VARCHAR(36),
                source_type VARCHAR(20) NOT NULL,
                pr_number INTEGER,
                pr_title VARCHAR(500),
                pr_url VARCHAR(1024),
                pr_author VARCHAR(255),
                submitted_by VARCHAR(36) REFERENCES users(id),
                code_snippet TEXT,
                language VARCHAR(50),
                diff TEXT,
                files_changed JSONB,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                overall_score INTEGER,
                overall_verdict VARCHAR(30),
                summary TEXT,
                github_comment_id VARCHAR(255),
                github_comment_posted BOOLEAN NOT NULL DEFAULT false,
                custom_instructions TEXT,
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_reviews_org ON code_reviews(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_reviews_repo ON code_reviews(repo_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_reviews_status ON code_reviews(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_reviews_source ON code_reviews(source_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_reviews_pr ON code_reviews(pr_number)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_reviews_created ON code_reviews(created_at DESC)"))
        print("[OK] Tabela code_reviews criada")

        # 2. review_findings
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_findings (
                id VARCHAR(36) PRIMARY KEY,
                review_id VARCHAR(36) NOT NULL REFERENCES code_reviews(id) ON DELETE CASCADE,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                category VARCHAR(20) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                suggestion TEXT,
                file_path VARCHAR(1024),
                line_start INTEGER,
                line_end INTEGER,
                code_snippet TEXT,
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_findings_review ON review_findings(review_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_findings_org ON review_findings(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_findings_category ON review_findings(category)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_review_findings_severity ON review_findings(severity)"))
        print("[OK] Tabela review_findings criada")

    print("\n[DONE] Migration Revisao de Codigo concluida!")


if __name__ == "__main__":
    migrate()
