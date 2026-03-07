"""
Executa todas as migrations do Memora em ordem, com idempotencia.

Uso: python scripts/run_all_migrations.py

- Cria tabela migration_log para rastrear execucoes
- Roda setup_tables.py primeiro (sempre — e idempotente)
- Executa cada migrate_*.py em ordem alfabetica, pulando ja executados
- Roda seed_admin.py por ultimo (apenas se nao houver admin no banco)
"""

import importlib.util
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPTS_DIR.parent

# Adiciona raiz do projeto ao sys.path para que scripts possam importar 'app'
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        print("[ERRO] DATABASE_URL nao configurada no .env")
        sys.exit(1)
    return psycopg2.connect(DATABASE_URL)


def ensure_migration_log(conn):
    """Cria tabela migration_log se nao existir."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS migration_log (
            id SERIAL PRIMARY KEY,
            script_name VARCHAR(255) NOT NULL UNIQUE,
            executed_at TIMESTAMP DEFAULT now(),
            success BOOLEAN NOT NULL
        );
    """)
    conn.commit()
    cur.close()


def is_already_executed(conn, script_name: str) -> bool:
    """Verifica se um script ja foi executado com sucesso."""
    cur = conn.cursor()
    cur.execute(
        "SELECT success FROM migration_log WHERE script_name = %s AND success = true",
        (script_name,),
    )
    result = cur.fetchone()
    cur.close()
    return result is not None


def record_execution(conn, script_name: str, success: bool):
    """Registra resultado da execucao no migration_log."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO migration_log (script_name, success)
        VALUES (%s, %s)
        ON CONFLICT (script_name) DO UPDATE SET
            success = EXCLUDED.success,
            executed_at = now()
        """,
        (script_name, success),
    )
    conn.commit()
    cur.close()


def run_script(script_path: Path) -> bool:
    """Executa um script Python carregando seu modulo dinamicamente."""
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    if spec is None or spec.loader is None:
        print(f"  [ERRO] Nao foi possivel carregar: {script_path.name}")
        return False

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        if hasattr(module, "run"):
            module.run()
        elif hasattr(module, "migrate"):
            module.migrate()
        return True
    except SystemExit:
        # Alguns scripts chamam sys.exit() em caso de erro
        return False
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False


def has_admin(conn) -> bool:
    """Verifica se ja existe um admin no banco."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        count = cur.fetchone()[0]
        return count > 0
    except Exception:
        return False
    finally:
        cur.close()


def main():
    conn = get_connection()
    ensure_migration_log(conn)

    print("=" * 60)
    print("  Memora — Migration Runner")
    print("=" * 60)
    print()

    # 1. setup_tables.py (sempre roda — e idempotente)
    setup_script = SCRIPTS_DIR / "setup_tables.py"
    if setup_script.exists():
        print("[RUN]  setup_tables.py (idempotente)")
        success = run_script(setup_script)
        status = "OK" if success else "ERRO"
        print(f"[{status}]  setup_tables.py")
        record_execution(conn, "setup_tables.py", success)
        if not success:
            print("\n[ERRO] setup_tables.py falhou. Abortando.")
            conn.close()
            sys.exit(1)
    else:
        print("[WARN] setup_tables.py nao encontrado")

    print()

    # 2. migrate_*.py em ordem alfabetica
    migration_scripts = sorted(SCRIPTS_DIR.glob("migrate_*.py"))

    if not migration_scripts:
        print("[INFO] Nenhum script de migracao encontrado")
    else:
        for script_path in migration_scripts:
            name = script_path.name

            if is_already_executed(conn, name):
                print(f"[SKIP] {name} — ja executado")
                continue

            print(f"[RUN]  {name}")
            success = run_script(script_path)

            if success:
                print(f"[OK]   {name} — executado com sucesso")
                record_execution(conn, name, True)
            else:
                print(f"[ERRO] {name} — falhou")
                record_execution(conn, name, False)

    print()

    # 3. seed_admin.py (apenas se nao houver admin)
    seed_script = SCRIPTS_DIR / "seed_admin.py"
    if seed_script.exists():
        if has_admin(conn):
            print("[SKIP] seed_admin.py — admin ja existe")
        else:
            print("[RUN]  seed_admin.py")
            success = run_script(seed_script)
            status = "OK" if success else "ERRO"
            print(f"[{status}]  seed_admin.py")
    else:
        print("[WARN] seed_admin.py nao encontrado")

    print()
    print("=" * 60)
    print("  Migrations concluidas!")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
