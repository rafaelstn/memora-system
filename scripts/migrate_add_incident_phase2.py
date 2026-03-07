"""Fase 2 de incidentes: share_token, incident_similar_incidents."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # Add share_token to incidents (for public post-mortem sharing)
        conn.execute(text("""
            ALTER TABLE incidents
            ADD COLUMN IF NOT EXISTS share_token VARCHAR(64) UNIQUE
        """))
        print("Coluna share_token adicionada a incidents.")

        # Create incident_similar_incidents table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS incident_similar_incidents (
                id VARCHAR(36) PRIMARY KEY,
                incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id),
                similar_incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id),
                similarity_score FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_similar_incident
            ON incident_similar_incidents(incident_id)
        """))
        print("Tabela incident_similar_incidents criada.")

    print("Migracao fase 2 de incidentes concluida.")


if __name__ == "__main__":
    migrate()
