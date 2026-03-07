"""Cria tabelas business_rules, rule_change_alerts e rule_simulations."""

from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # business_rules
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS business_rules (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                repo_name VARCHAR(255) NOT NULL,
                rule_type VARCHAR(20) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                plain_english TEXT NOT NULL,
                conditions JSONB,
                affected_files JSONB,
                affected_functions JSONB,
                embedding vector(1536),
                confidence FLOAT NOT NULL DEFAULT 0.0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                last_verified_at TIMESTAMP,
                changed_in_last_push BOOLEAN NOT NULL DEFAULT false,
                extracted_at TIMESTAMP DEFAULT now(),
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))

        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rules_org ON business_rules(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rules_repo ON business_rules(repo_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rules_type ON business_rules(rule_type)"))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rules_embedding
            ON business_rules USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))

        # rule_change_alerts
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rule_change_alerts (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                rule_id VARCHAR(36) NOT NULL REFERENCES business_rules(id),
                change_type VARCHAR(20) NOT NULL,
                previous_description TEXT,
                new_description TEXT,
                detected_at TIMESTAMP DEFAULT now(),
                acknowledged_by VARCHAR(36) REFERENCES users(id),
                acknowledged_at TIMESTAMP
            )
        """))

        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rule_alerts_org ON rule_change_alerts(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rule_alerts_rule ON rule_change_alerts(rule_id)"))

        # rule_simulations
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rule_simulations (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                rule_id VARCHAR(36) NOT NULL REFERENCES business_rules(id),
                simulated_by VARCHAR(36) NOT NULL REFERENCES users(id),
                input_values JSONB NOT NULL,
                result TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT now()
            )
        """))

        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simulations_org ON rule_simulations(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simulations_rule ON rule_simulations(rule_id)"))

    print("Tabelas business_rules, rule_change_alerts e rule_simulations criadas com sucesso.")


if __name__ == "__main__":
    migrate()
