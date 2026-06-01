from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
LOCAL_PACKAGES = PROJECT_ROOT / ".codex-python-packages"
if LOCAL_PACKAGES.exists():
    sys.path.append(str(LOCAL_PACKAGES))
sys.path.insert(0, str(ROOT))

from modules.env_loader import load_env_file

load_env_file(ROOT / ".env")

try:
    import psycopg
    from psycopg import sql
except ImportError as error:
    raise SystemExit(
        "Dependency PostgreSQL belum tersedia. Jalankan `pip install -r backend/requirements.txt`."
    ) from error


def identifier_parts(table_name):
    return [part.strip() for part in table_name.split(".") if part.strip()]


def main():
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not database_url:
        raise SystemExit("Set DATABASE_URL di backend/.env terlebih dahulu.")

    table_name = os.environ.get("JOBS_TABLE", "jobs")
    parts = identifier_parts(table_name)
    if not parts:
        raise SystemExit("JOBS_TABLE tidak valid.")

    table_identifier = sql.Identifier(*parts)

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(table_identifier))
            total_jobs = cursor.fetchone()[0]
            cursor.execute(
                sql.SQL(
                    "SELECT COUNT(DISTINCT fingerprint) FROM {} "
                    "WHERE fingerprint IS NOT NULL AND fingerprint <> ''"
                ).format(table_identifier)
            )
            unique_fingerprints = cursor.fetchone()[0]

    print(f"Koneksi PostgreSQL berhasil.")
    print(f"Tabel: {table_name}")
    print(f"Total jobs: {total_jobs}")
    print(f"Unique fingerprints: {unique_fingerprints}")


if __name__ == "__main__":
    main()
