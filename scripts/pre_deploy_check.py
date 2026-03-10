"""Verificacoes pre-deploy — executa antes de iniciar o sistema em producao."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check():
    errors = []

    # 1. LLM_ENCRYPTION_KEY
    key = os.environ.get("LLM_ENCRYPTION_KEY", "")
    if not key:
        errors.append(
            "LLM_ENCRYPTION_KEY nao configurada. "
            "Gere com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    # 2. DATABASE_URL
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "localhost" in db_url:
        errors.append("DATABASE_URL nao configurada ou apontando para localhost")

    # 3. Supabase
    for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"]:
        if not os.environ.get(var, ""):
            errors.append(f"{var} nao configurada")

    # 4. OPENAI_API_KEY (required for embeddings)
    if not os.environ.get("OPENAI_API_KEY", ""):
        errors.append("OPENAI_API_KEY nao configurada (necessaria para embeddings)")

    if errors:
        print("\n===== PRE-DEPLOY CHECK FAILED =====")
        for e in errors:
            print(f"  ✗ {e}")
        print("====================================\n")
        sys.exit(1)
    else:
        print("✓ Todas as verificacoes pre-deploy passaram.")


if __name__ == "__main__":
    check()
