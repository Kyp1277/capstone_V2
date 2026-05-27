import os

import pandas as pd


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


def _clean_dataframe(df):
    df = df.fillna("Unknown")
    df = df.drop_duplicates()
    return df.reset_index(drop=True)


def _load_jobs_from_csv(file_path):
    df = pd.read_csv(file_path)
    return _clean_dataframe(df).to_dict(orient="records")


def _identifier_parts(table_name):
    return [part.strip() for part in table_name.split(".") if part.strip()]


def _load_jobs_from_postgres(database_url, table_name):
    try:
        import psycopg
        from psycopg import sql
    except ImportError as error:
        raise RuntimeError(
            "Dependency PostgreSQL belum tersedia. Jalankan `pip install -r backend/requirements.txt`."
        ) from error

    parts = _identifier_parts(table_name)
    if not parts:
        raise RuntimeError("JOBS_TABLE tidak valid.")

    table_identifier = sql.Identifier(*parts)
    columns = [sql.Identifier(column) for column in JOB_COLUMNS]
    query = sql.SQL("SELECT {} FROM {} ORDER BY job_no").format(
        sql.SQL(", ").join(columns),
        table_identifier,
    )

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    df = pd.DataFrame(rows, columns=JOB_COLUMNS)
    return _clean_dataframe(df).to_dict(orient="records")


# =========================================
# LOAD DATASET
# =========================================
def load_jobs(file_path):
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    source = os.environ.get("JOBS_SOURCE", "postgres" if database_url else "csv").strip().lower()

    if source in {"postgres", "postgresql", "db", "database"}:
        if not database_url:
            raise RuntimeError("DATABASE_URL wajib diisi saat JOBS_SOURCE=postgres.")

        table_name = os.environ.get("JOBS_TABLE", "jobs")
        return _load_jobs_from_postgres(database_url, table_name)

    if source != "csv":
        raise RuntimeError("JOBS_SOURCE hanya mendukung nilai `csv` atau `postgres`.")

    return _load_jobs_from_csv(file_path)
