from pathlib import Path
import os
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
LOCAL_PACKAGES = PROJECT_ROOT / ".codex-python-packages"
if LOCAL_PACKAGES.exists():
    sys.path.insert(0, str(LOCAL_PACKAGES))
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


JOB_COLUMNS = [
    "job_no",
    "title",
    "company",
    "location",
    "keyword",
    "job_url",
    "description",
    "scraped_at",
    "fingerprint",
]


def load_csv(path):
    df = pd.read_csv(path)
    missing_columns = [column for column in JOB_COLUMNS if column not in df.columns]
    if missing_columns:
        raise SystemExit(f"Kolom dataset tidak lengkap: {', '.join(missing_columns)}")

    df = df[JOB_COLUMNS].fillna("Unknown")
    df["job_no"] = pd.to_numeric(df["job_no"], errors="coerce")
    df = df.dropna(subset=["job_no"])
    df["job_no"] = df["job_no"].astype(int)
    df = df.drop_duplicates(subset=["job_no"], keep="last")
    df = df.drop_duplicates(subset=["fingerprint"], keep="last")
    return df.reset_index(drop=True)


def identifier_parts(table_name):
    return [part.strip() for part in table_name.split(".") if part.strip()]


def index_name(table_name, suffix):
    base_name = table_name.split(".")[-1].strip() or "jobs"
    safe_name = "".join(char if char.isalnum() or char == "_" else "_" for char in base_name)
    return f"idx_{safe_name}_{suffix}"


def main():
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not database_url:
        raise SystemExit("Set DATABASE_URL terlebih dahulu.")

    table_name = os.environ.get("JOBS_TABLE", "jobs")
    if not table_name.replace("_", "").replace(".", "").isalnum():
        raise SystemExit("JOBS_TABLE tidak valid.")

    csv_path = Path(os.environ.get("JOBS_CSV_PATH", ROOT / "data" / "jobs_clean.csv"))
    df = load_csv(csv_path)
    table_identifier = sql.Identifier(*identifier_parts(table_name))
    column_identifiers = [sql.Identifier(column) for column in JOB_COLUMNS]

    create_table_query = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {} (
            job_no INTEGER PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            keyword TEXT,
            job_url TEXT,
            description TEXT,
            scraped_at TEXT,
            fingerprint TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """).format(table_identifier)

    alter_table_queries = [
        sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()").format(table_identifier),
        sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()").format(table_identifier),
    ]

    index_queries = [
        sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (keyword)").format(sql.Identifier(index_name(table_name, "keyword")), table_identifier),
        sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (title)").format(sql.Identifier(index_name(table_name, "title")), table_identifier),
        sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (company)").format(sql.Identifier(index_name(table_name, "company")), table_identifier),
        sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (location)").format(sql.Identifier(index_name(table_name, "location")), table_identifier),
        sql.SQL("CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} (fingerprint) WHERE fingerprint IS NOT NULL AND fingerprint <> ''").format(
            sql.Identifier(index_name(table_name, "fingerprint")),
            table_identifier,
        ),
    ]

    insert_query = sql.SQL("""
        INSERT INTO {} ({})
        VALUES ({})
        ON CONFLICT (fingerprint) WHERE fingerprint IS NOT NULL AND fingerprint <> '' DO UPDATE SET {}
    """).format(
        table_identifier,
        sql.SQL(", ").join(column_identifiers),
        sql.SQL(", ").join([sql.Placeholder()] * len(JOB_COLUMNS)),
        sql.SQL(", ").join(
            [
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
                for column in JOB_COLUMNS
                if column != "job_no"
            ]
            + [
                sql.SQL("job_no = EXCLUDED.job_no"),
                sql.SQL("updated_at = NOW()"),
            ]
        ),
    )

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(create_table_query)
            for query in alter_table_queries:
                cursor.execute(query)
            for query in index_queries:
                cursor.execute(query)
            cursor.executemany(insert_query, df.itertuples(index=False, name=None))
        connection.commit()

    print(f"Berhasil import {len(df)} lowongan ke tabel {table_name}.")


if __name__ == "__main__":
    main()
