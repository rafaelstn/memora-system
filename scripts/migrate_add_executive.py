"""Cria tabela executive_snapshots."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS executive_snapshots (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL,
                generated_at TIMESTAMP NOT NULL DEFAULT now(),
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                health_score INTEGER NOT NULL DEFAULT 100,
                summary TEXT,
                highlights JSONB,
                risks JSONB,
                recommendations JSONB,
                metrics JSONB,
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exec_snap_org ON executive_snapshots(org_id)"))
        print("Tabela executive_snapshots criada.")

    print("Migracao de snapshots executivos concluida.")


if __name__ == "__main__":
    migrate()
