"""
Limpa TODOS os dados do banco e do Supabase Auth.
Nao dropa tabelas — apenas deleta registros.

Uso: python scripts/reset_db.py
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

TABLES_IN_ORDER = [
    "messages",
    "conversations",
    "code_chunks",
    "invites",
    "github_integration",
    "users",
]


def run():
    if not DATABASE_URL:
        print("DATABASE_URL nao configurada no .env")
        sys.exit(1)

    print()
    print("ATENCAO: Isso apaga TODOS os dados do sistema.")
    print("Tabelas que serao limpas: " + ", ".join(TABLES_IN_ORDER))
    print()
    confirm = input("Digite CONFIRMAR para continuar: ")
    if confirm != "CONFIRMAR":
        print("Cancelado.")
        sys.exit(0)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print()
    for table in TABLES_IN_ORDER:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {table}")
            print(f"  {table}: {count} registros deletados")
        except Exception as e:
            print(f"  {table}: erro ({e})")

    cur.close()
    conn.close()

    # Limpar Supabase Auth
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        print()
        print("Limpando usuarios do Supabase Auth...")
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        }
        try:
            resp = httpx.get(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=headers,
                params={"per_page": 1000},
                timeout=10,
            )
            if resp.status_code == 200:
                users = resp.json().get("users", [])
                deleted = 0
                for u in users:
                    del_resp = httpx.delete(
                        f"{SUPABASE_URL}/auth/v1/admin/users/{u['id']}",
                        headers=headers,
                        timeout=10,
                    )
                    if del_resp.status_code in (200, 204):
                        deleted += 1
                print(f"  Supabase Auth: {deleted} usuarios deletados")
            else:
                print(f"  Erro ao listar usuarios: {resp.status_code}")
        except Exception as e:
            print(f"  Erro no Supabase Auth: {e}")
    else:
        print("  SUPABASE_URL/SERVICE_ROLE_KEY nao configurados — pulando limpeza de Auth")

    print()
    print("Reset concluido!")


if __name__ == "__main__":
    run()
