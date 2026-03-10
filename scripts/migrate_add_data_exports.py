"""Migration: cria tabela data_exports para rastreamento de exportacoes."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from sqlalchemy import text

SQL = """
CREATE TABLE IF NOT EXISTS data_exports (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36),
    requested_by VARCHAR(36) NOT NULL,
    format VARCHAR(10) NOT NULL DEFAULT 'json',
    period_start DATE,
    period_end DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    file_path TEXT,
    file_size_bytes BIGINT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_data_exports_org ON data_exports(org_id, created_at DESC);
"""

if __name__ == "__main__":
    with engine.begin() as conn:
        for stmt in SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("Migration data_exports concluida.")
