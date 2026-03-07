"""
Cria o usuario admin via Supabase Auth se nao existir.
Pede credenciais por argumento ou interativamente.

Uso:
  python scripts/seed_admin.py                    # interativo
  python scripts/seed_admin.py email@ex.com senha # por argumento
"""

import os
import sys
from pathlib import Path

import httpx
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def run():
    if not DATABASE_URL:
        print("DATABASE_URL nao configurada no .env")
        sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY sao obrigatorios no .env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"Admin ja existe ({count} encontrado(s)). Pulando seed.")
        cur.close()
        conn.close()
        return False

    # Obter credenciais
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
    elif os.getenv("ADMIN_EMAIL") and os.getenv("ADMIN_PASSWORD"):
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")
    else:
        print("Nenhum admin encontrado. Vamos criar um.")
        email = input("  Email do admin: ").strip()
        if not email:
            print("Email obrigatorio.")
            sys.exit(1)
        password = input("  Senha (min 8 chars): ").strip()
        if len(password) < 8:
            print("Senha deve ter no minimo 8 caracteres.")
            sys.exit(1)

    name = os.getenv("ADMIN_NAME") or input("  Nome do admin: ").strip() or "Admin"

    resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers={
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
        },
        timeout=10,
    )

    if resp.status_code not in (200, 201):
        print(f"Erro ao criar usuario no Supabase Auth: {resp.status_code} {resp.text}")
        sys.exit(1)

    supabase_uid = resp.json()["id"]

    cur.execute(
        """
        INSERT INTO users (id, name, email, role, is_active)
        VALUES (%s, %s, %s, 'admin', true)
        ON CONFLICT (id) DO NOTHING
        """,
        (supabase_uid, name, email),
    )

    print(f"Admin criado: {email} (ID: {supabase_uid})")
    cur.close()
    conn.close()
    return True


if __name__ == "__main__":
    run()
