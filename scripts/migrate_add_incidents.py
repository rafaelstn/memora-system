"""Cria tabelas de incidentes: incidents, incident_timeline, incident_hypotheses."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # incidents
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS incidents (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                alert_id VARCHAR(36) REFERENCES error_alerts(id),
                project_id VARCHAR(36) NOT NULL REFERENCES monitored_projects(id),
                title VARCHAR(500) NOT NULL,
                description TEXT,
                severity VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'open',
                declared_by VARCHAR(36) NOT NULL REFERENCES users(id),
                declared_at TIMESTAMP NOT NULL DEFAULT now(),
                mitigated_at TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution_summary TEXT,
                postmortem TEXT,
                postmortem_generated_at TIMESTAMP,
                similar_incidents JSONB,
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_incidents_org ON incidents(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_incidents_project ON incidents(project_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)"))
        print("Tabela incidents criada.")

        # incident_timeline
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS incident_timeline (
                id VARCHAR(36) PRIMARY KEY,
                incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id),
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                event_type VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_by VARCHAR(36) REFERENCES users(id),
                is_ai_generated BOOLEAN NOT NULL DEFAULT false,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_timeline_incident ON incident_timeline(incident_id)"))
        print("Tabela incident_timeline criada.")

        # incident_hypotheses
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS incident_hypotheses (
                id VARCHAR(36) PRIMARY KEY,
                incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id),
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                hypothesis TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                confidence FLOAT NOT NULL DEFAULT 0.5,
                status VARCHAR(20) NOT NULL DEFAULT 'open',
                confirmed_by VARCHAR(36) REFERENCES users(id),
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hypotheses_incident ON incident_hypotheses(incident_id)"))
        print("Tabela incident_hypotheses criada.")

    print("Migracao de incidentes concluida.")


if __name__ == "__main__":
    migrate()
