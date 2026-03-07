"""Migration: adiciona campos de onboarding na tabela organizations."""

from sqlalchemy import text

from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        # 1. Adicionar onboarding_completed
        exists = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'organizations' AND column_name = 'onboarding_completed'
        """)).first()
        if not exists:
            conn.execute(text(
                "ALTER TABLE public.organizations ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT false"
            ))
            print("[OK] Coluna onboarding_completed adicionada")
        else:
            print("[SKIP] Coluna onboarding_completed ja existe")

        # 2. Adicionar onboarding_step
        exists = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'organizations' AND column_name = 'onboarding_step'
        """)).first()
        if not exists:
            conn.execute(text(
                "ALTER TABLE public.organizations ADD COLUMN onboarding_step INTEGER NOT NULL DEFAULT 0"
            ))
            print("[OK] Coluna onboarding_step adicionada")
        else:
            print("[SKIP] Coluna onboarding_step ja existe")

        # 3. Adicionar onboarding_completed_at
        exists = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'organizations' AND column_name = 'onboarding_completed_at'
        """)).first()
        if not exists:
            conn.execute(text(
                "ALTER TABLE public.organizations ADD COLUMN onboarding_completed_at TIMESTAMP"
            ))
            print("[OK] Coluna onboarding_completed_at adicionada")
        else:
            print("[SKIP] Coluna onboarding_completed_at ja existe")

    print("\n[DONE] Migration onboarding concluida!")


if __name__ == "__main__":
    migrate()
