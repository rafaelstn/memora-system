"""Cria tabelas de produtos (products, product_memberships) e adiciona product_id nas tabelas existentes.

Migra registros existentes: cria um 'Produto Principal' por org e associa todos os dados a ele.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine


TABLES_WITH_PRODUCT_ID = [
    "code_chunks",
    "conversations",
    "monitored_projects",
    "code_reviews",
    "code_generations",
    "knowledge_entries",
    "business_rules",
    "impact_analyses",
    "security_scans",
    "dast_scans",
]


def migrate():
    with engine.begin() as conn:
        # 1. Criar tabela products
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id VARCHAR(36) PRIMARY KEY,
                org_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_org ON products(org_id)"))
        print("Tabela products criada.")

        # 2. Criar tabela product_memberships
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_memberships (
                id VARCHAR(36) PRIMARY KEY,
                product_id VARCHAR(36) NOT NULL REFERENCES products(id),
                user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT now(),
                CONSTRAINT uq_product_user UNIQUE (product_id, user_id)
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pm_product ON product_memberships(product_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pm_user ON product_memberships(user_id)"))
        print("Tabela product_memberships criada.")

        # 3. Adicionar product_id (nullable) nas tabelas existentes
        for table in TABLES_WITH_PRODUCT_ID:
            # Verifica se a coluna já existe
            exists = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table AND column_name = 'product_id'
            """), {"table": table}).first()

            if not exists:
                conn.execute(text(f"""
                    ALTER TABLE {table}
                    ADD COLUMN product_id VARCHAR(36) REFERENCES products(id)
                """))
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table}_product ON {table}(product_id)
                """))
                print(f"  Coluna product_id adicionada em {table}.")
            else:
                print(f"  Coluna product_id ja existe em {table}, pulando.")

        # 4. Criar produto padrão por org e migrar dados existentes
        orgs = conn.execute(text("SELECT id FROM organizations")).fetchall()

        for (org_id,) in orgs:
            # Verifica se já tem produto para essa org
            existing = conn.execute(text("""
                SELECT id FROM products WHERE org_id = :org_id LIMIT 1
            """), {"org_id": org_id}).first()

            if existing:
                product_id = existing[0]
                print(f"  Org {org_id} ja tem produto ({product_id}), reutilizando.")
            else:
                import uuid
                product_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO products (id, org_id, name, description, is_active)
                    VALUES (:id, :org_id, 'Produto Principal', 'Produto padrão criado automaticamente na migração', true)
                """), {"id": product_id, "org_id": org_id})
                print(f"  Produto Principal criado para org {org_id}: {product_id}")

            # Associar dados existentes ao produto
            for table in TABLES_WITH_PRODUCT_ID:
                # Só atualiza registros que têm org_id e product_id NULL
                has_org_id = conn.execute(text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = :table AND column_name = 'org_id'
                """), {"table": table}).first()

                if has_org_id:
                    result = conn.execute(text(f"""
                        UPDATE {table}
                        SET product_id = :product_id
                        WHERE org_id = :org_id AND product_id IS NULL
                    """), {"product_id": product_id, "org_id": org_id})
                    if result.rowcount > 0:
                        print(f"    {table}: {result.rowcount} registros migrados.")

            # Adicionar todos os users da org como membros do produto
            users = conn.execute(text("""
                SELECT id FROM users WHERE org_id = :org_id AND is_active = true
            """), {"org_id": org_id}).fetchall()

            for (user_id,) in users:
                already_member = conn.execute(text("""
                    SELECT 1 FROM product_memberships
                    WHERE product_id = :product_id AND user_id = :user_id
                """), {"product_id": product_id, "user_id": user_id}).first()

                if not already_member:
                    import uuid
                    conn.execute(text("""
                        INSERT INTO product_memberships (id, product_id, user_id)
                        VALUES (:id, :product_id, :user_id)
                    """), {"id": str(uuid.uuid4()), "product_id": product_id, "user_id": user_id})

            if users:
                print(f"    {len(users)} usuarios adicionados como membros do produto.")

    print("\nMigracao de produtos concluida com sucesso.")


if __name__ == "__main__":
    migrate()
