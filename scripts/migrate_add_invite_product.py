"""Adiciona coluna product_id opcional na tabela invites."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        exists = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'invites' AND column_name = 'product_id'
        """)).first()

        if not exists:
            conn.execute(text("""
                ALTER TABLE invites ADD COLUMN product_id VARCHAR(36)
            """))
            print("Coluna product_id adicionada em invites.")
        else:
            print("Coluna product_id ja existe em invites, pulando.")

    print("\nMigracao invite_product concluida com sucesso.")


if __name__ == "__main__":
    migrate()
