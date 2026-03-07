"""Migration: adiciona tabelas do Monitor de Erros (Modulo 2)."""
from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # 1. monitored_projects
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS monitored_projects (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                name VARCHAR(255) NOT NULL,
                description VARCHAR(500),
                token VARCHAR(255) UNIQUE NOT NULL,
                token_preview VARCHAR(8) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by VARCHAR(36) NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_monitored_projects_org ON monitored_projects(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_monitored_projects_token ON monitored_projects(token)"))
        print("[OK] Tabela monitored_projects criada")

        # 2. log_entries
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS log_entries (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL REFERENCES monitored_projects(id),
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                level VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                source VARCHAR(500),
                stack_trace TEXT,
                metadata JSONB,
                received_at TIMESTAMP DEFAULT now(),
                occurred_at TIMESTAMP,
                is_analyzed BOOLEAN NOT NULL DEFAULT false,
                raw_payload JSONB
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_entries_project ON log_entries(project_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_entries_org ON log_entries(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_log_entries_received ON log_entries(received_at DESC)"))
        print("[OK] Tabela log_entries criada")

        # 3. error_alerts
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS error_alerts (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL REFERENCES monitored_projects(id),
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                log_entry_id VARCHAR(36) NOT NULL REFERENCES log_entries(id),
                title VARCHAR(500) NOT NULL,
                explanation TEXT NOT NULL,
                severity VARCHAR(20) NOT NULL,
                affected_component VARCHAR(255),
                suggested_actions JSONB,
                status VARCHAR(20) NOT NULL DEFAULT 'open',
                acknowledged_by VARCHAR(36) REFERENCES users(id),
                acknowledged_at TIMESTAMP,
                resolved_by VARCHAR(36) REFERENCES users(id),
                resolved_at TIMESTAMP,
                notification_sent BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_error_alerts_project ON error_alerts(project_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_error_alerts_org ON error_alerts(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_error_alerts_status ON error_alerts(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_error_alerts_severity ON error_alerts(severity)"))
        print("[OK] Tabela error_alerts criada")

        # 4. alert_webhooks
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_webhooks (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                name VARCHAR(255) NOT NULL,
                url TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by VARCHAR(36) NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_alert_webhooks_org ON alert_webhooks(org_id)"))
        print("[OK] Tabela alert_webhooks criada")

    print("\n[DONE] Migration Monitor de Erros concluida!")


if __name__ == "__main__":
    migrate()
