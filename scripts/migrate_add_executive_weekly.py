"""Migration: cria tabela executive_weekly_snapshots para historico semanal."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from sqlalchemy import text

SQL = """
CREATE TABLE IF NOT EXISTS executive_weekly_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    security_score_avg FLOAT,
    error_alert_count INTEGER DEFAULT 0,
    support_question_count INTEGER DEFAULT 0,
    code_review_score_avg FLOAT,
    prs_reviewed_count INTEGER DEFAULT 0,
    incident_resolution_avg_hours FLOAT,
    doc_coverage_pct FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_exec_weekly_org ON executive_weekly_snapshots(org_id, product_id, week_start);
"""

if __name__ == "__main__":
    with engine.begin() as conn:
        for stmt in SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("Migration executive_weekly_snapshots concluida.")
