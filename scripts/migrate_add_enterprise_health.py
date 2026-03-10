"""Adiciona colunas de health check em enterprise_db_configs e cria tabela enterprise_db_health_log."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # 1. Adicionar colunas de health em enterprise_db_configs
        for col, dtype, default in [
            ("last_health_check", "TIMESTAMP", None),
            ("last_health_status", "VARCHAR(20)", None),
            ("last_health_error", "TEXT", None),
        ]:
            exists = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'enterprise_db_configs' AND column_name = :col
            """), {"col": col}).first()

            if not exists:
                stmt = f"ALTER TABLE enterprise_db_configs ADD COLUMN {col} {dtype}"
                if default is not None:
                    stmt += f" DEFAULT {default}"
                conn.execute(text(stmt))
                print(f"  Coluna {col} adicionada em enterprise_db_configs.")
            else:
                print(f"  Coluna {col} ja existe, pulando.")

        # 2. Criar tabela enterprise_db_health_log
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS enterprise_db_health_log (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                status VARCHAR(20) NOT NULL,
                response_time_ms INTEGER,
                error_message TEXT,
                checked_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_edb_health_org ON enterprise_db_health_log(org_id)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_edb_health_checked ON enterprise_db_health_log(checked_at DESC)"
        ))
        print("  Tabela enterprise_db_health_log criada.")

    print("\nMigracao enterprise_health concluida com sucesso.")


if __name__ == "__main__":
    migrate()
