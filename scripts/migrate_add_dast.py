"""Create DAST scanner tables."""
from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dast_scans (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                requested_by VARCHAR(36) NOT NULL REFERENCES users(id),
                target_url VARCHAR NOT NULL,
                target_env VARCHAR NOT NULL DEFAULT 'development',
                status VARCHAR NOT NULL DEFAULT 'pending',
                probes_total INTEGER DEFAULT 0,
                probes_completed INTEGER DEFAULT 0,
                vulnerabilities_confirmed INTEGER DEFAULT 0,
                risk_level VARCHAR,
                summary TEXT,
                duration_seconds INTEGER,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS idx_dast_scans_org
                ON dast_scans(org_id);

            CREATE TABLE IF NOT EXISTS dast_findings (
                id VARCHAR(36) PRIMARY KEY,
                scan_id VARCHAR(36) NOT NULL REFERENCES dast_scans(id) ON DELETE CASCADE,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                probe_type VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                description TEXT NOT NULL,
                result TEXT NOT NULL,
                confirmed BOOLEAN DEFAULT false,
                endpoint VARCHAR NOT NULL,
                payload_used TEXT,
                response_code INTEGER,
                recommendation TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS idx_dast_findings_scan
                ON dast_findings(scan_id);
        """))
    print("DAST tables created.")


if __name__ == "__main__":
    migrate()
