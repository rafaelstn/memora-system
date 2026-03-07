"""Cria tabelas code_generations e mcp_tokens para o Modulo 7."""

from app.db.session import engine
from sqlalchemy import text


def run():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS code_generations (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                repo_name VARCHAR(255) NOT NULL,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                request_description TEXT NOT NULL,
                request_type VARCHAR(50) NOT NULL,
                file_path VARCHAR(1024),
                use_context BOOLEAN DEFAULT true,
                context_used JSONB,
                generated_code TEXT,
                explanation TEXT,
                model_used VARCHAR(100),
                tokens_used FLOAT,
                cost_usd FLOAT,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_code_generations_org
            ON code_generations(org_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_code_generations_user
            ON code_generations(user_id);
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_tokens (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                token_hash VARCHAR(255) NOT NULL UNIQUE,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT now(),
                revoked_at TIMESTAMPTZ
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_mcp_tokens_org
            ON mcp_tokens(org_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_mcp_tokens_user
            ON mcp_tokens(user_id);
        """))

    print("Tabelas code_generations e mcp_tokens criadas com sucesso.")


if __name__ == "__main__":
    run()
