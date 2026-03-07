"""Migration: adiciona multi-tenancy (organizations + org_id em todas as tabelas)."""
import uuid

from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # 1. Criar tabela organizations
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS organizations (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT now(),
                settings JSONB DEFAULT '{}'::jsonb
            )
        """))
        print("[OK] Tabela organizations criada")

        # 2. Adicionar org_id em todas as tabelas
        tables_to_update = ["users", "code_chunks", "conversations", "invites", "github_integration"]
        for table in tables_to_update:
            # Check if column exists
            exists = conn.execute(text(f"""
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = '{table}' AND column_name = 'org_id'
            """)).first()
            if not exists:
                conn.execute(text(f"ALTER TABLE public.{table} ADD COLUMN org_id VARCHAR(36)"))
                print(f"[OK] Coluna org_id adicionada em {table}")
            else:
                print(f"[SKIP] Coluna org_id ja existe em {table}")

        # 3. Se existem dados sem org_id, criar org default e associar
        orphan_users = conn.execute(text(
            "SELECT id, name FROM public.users WHERE org_id IS NULL LIMIT 1"
        )).first()

        if orphan_users:
            default_org_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO organizations (id, name, slug)
                VALUES (:id, 'Organização Padrão', 'org-default')
                ON CONFLICT (slug) DO NOTHING
            """), {"id": default_org_id})

            # Pega o id real (pode já existir)
            org = conn.execute(text(
                "SELECT id FROM organizations WHERE slug = 'org-default'"
            )).first()
            org_id = org[0]

            for table in tables_to_update:
                result = conn.execute(text(
                    f"UPDATE public.{table} SET org_id = :org_id WHERE org_id IS NULL"
                ), {"org_id": org_id})
                if result.rowcount > 0:
                    print(f"[OK] {result.rowcount} registros de {table} associados à org default")

        # 4. Setar NOT NULL (apenas se todos os registros já têm org_id)
        for table in tables_to_update:
            null_count = conn.execute(text(
                f"SELECT COUNT(*) FROM public.{table} WHERE org_id IS NULL"
            )).scalar()
            if null_count == 0:
                try:
                    conn.execute(text(
                        f"ALTER TABLE public.{table} ALTER COLUMN org_id SET NOT NULL"
                    ))
                    print(f"[OK] org_id NOT NULL em {table}")
                except Exception as e:
                    print(f"[WARN] Não foi possível setar NOT NULL em {table}: {e}")

        # 5. Criar indices
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_org_id ON public.users(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_chunks_org_id ON public.code_chunks(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_org_id ON public.conversations(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_invites_org_id ON public.invites(org_id)"))
        print("[OK] Indices criados")

    print("\n[DONE] Migration multi-tenancy concluída!")


if __name__ == "__main__":
    migrate()
