"""Cria tabelas de analise de impacto: impact_analyses, impact_findings."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS impact_analyses (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                repo_name VARCHAR(255) NOT NULL,
                requested_by VARCHAR(36) NOT NULL REFERENCES users(id),
                change_description TEXT NOT NULL,
                affected_files JSONB,
                risk_level VARCHAR(20),
                risk_summary TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_impact_org ON impact_analyses(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_impact_repo ON impact_analyses(repo_name)"))
        print("Tabela impact_analyses criada.")

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS impact_findings (
                id VARCHAR(36) PRIMARY KEY,
                analysis_id VARCHAR(36) NOT NULL REFERENCES impact_analyses(id),
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                finding_type VARCHAR(30) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                affected_component VARCHAR(255),
                file_path VARCHAR(500),
                related_rule_id VARCHAR(36),
                related_entry_id VARCHAR(36),
                recommendation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_findings_analysis ON impact_findings(analysis_id)"))
        print("Tabela impact_findings criada.")

    print("Migracao de analise de impacto concluida.")


if __name__ == "__main__":
    migrate()
