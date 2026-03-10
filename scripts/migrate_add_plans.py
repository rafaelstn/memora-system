"""Adiciona tabela org_plans e plan_contacts para controle de planos e trial."""
import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.db.session import engine  # noqa: E402


def run():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS org_plans (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                plan VARCHAR(20) NOT NULL DEFAULT 'pro_trial',
                trial_started_at TIMESTAMP,
                trial_ends_at TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                activated_by VARCHAR(36),
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_org_plans_org_id ON org_plans(org_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_org_plans_org_id_unique ON org_plans(org_id);
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plan_contacts (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                user_id VARCHAR(36) NOT NULL,
                user_name VARCHAR(255),
                user_email VARCHAR(255),
                contact_reason VARCHAR(50) NOT NULL,
                message TEXT,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_plan_contacts_org_id ON plan_contacts(org_id);
            CREATE INDEX IF NOT EXISTS idx_plan_contacts_is_read ON plan_contacts(is_read);
        """))

        conn.commit()
        print("Tabelas org_plans e plan_contacts criadas com sucesso.")


if __name__ == "__main__":
    run()
