"""Create security analyzer tables."""
from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS security_scans (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID NOT NULL REFERENCES organizations(id),
                repo_name VARCHAR NOT NULL,
                requested_by UUID NOT NULL REFERENCES users(id),
                status VARCHAR DEFAULT 'pending',
                security_score INTEGER,
                total_findings INTEGER DEFAULT 0,
                critical_count INTEGER DEFAULT 0,
                high_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                low_count INTEGER DEFAULT 0,
                scanners_run JSONB DEFAULT '[]'::jsonb,
                duration_seconds INTEGER,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS idx_security_scans_org
                ON security_scans(org_id);
            CREATE INDEX IF NOT EXISTS idx_security_scans_repo
                ON security_scans(org_id, repo_name);

            CREATE TABLE IF NOT EXISTS security_findings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                scan_id UUID NOT NULL REFERENCES security_scans(id) ON DELETE CASCADE,
                org_id UUID NOT NULL REFERENCES organizations(id),
                scanner VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                description TEXT NOT NULL,
                file_path VARCHAR,
                line_start INTEGER,
                line_end INTEGER,
                code_snippet TEXT,
                recommendation TEXT,
                cwe_id VARCHAR,
                created_at TIMESTAMPTZ DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS idx_security_findings_scan
                ON security_findings(scan_id);
            CREATE INDEX IF NOT EXISTS idx_security_findings_severity
                ON security_findings(scan_id, severity);

            CREATE TABLE IF NOT EXISTS dependency_alerts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                scan_id UUID NOT NULL REFERENCES security_scans(id) ON DELETE CASCADE,
                org_id UUID NOT NULL REFERENCES organizations(id),
                package_name VARCHAR NOT NULL,
                current_version VARCHAR,
                ecosystem VARCHAR,
                vulnerability_id VARCHAR,
                severity VARCHAR NOT NULL,
                summary TEXT,
                fixed_version VARCHAR,
                created_at TIMESTAMPTZ DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS idx_dependency_alerts_scan
                ON dependency_alerts(scan_id);
        """))
    print("Security tables created.")


if __name__ == "__main__":
    migrate()
