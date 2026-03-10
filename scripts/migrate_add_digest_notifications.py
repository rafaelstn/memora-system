"""Migration: cria tabelas weekly_digest_log e proactive_notifications_log."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from sqlalchemy import text

SQL = """
CREATE TABLE IF NOT EXISTS weekly_digest_log (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL,
    product_ids TEXT,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'sent',
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_digest_log_org ON weekly_digest_log(org_id, week_start);

CREATE TABLE IF NOT EXISTS proactive_notifications_log (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    org_id VARCHAR(36) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'banner',
    detail TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_proactive_notif_org ON proactive_notifications_log(org_id, notification_type);
CREATE INDEX IF NOT EXISTS idx_proactive_notif_active ON proactive_notifications_log(org_id, channel, resolved_at);
"""

if __name__ == "__main__":
    with engine.begin() as conn:
        for stmt in SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("Migration digest + proactive notifications concluida.")
