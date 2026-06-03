import os

from modules import config as _config  # noqa: F401
from fastapi import APIRouter

from modules import jobs_service


router = APIRouter()


@router.get("/health")
def health():
    jobs_source = os.environ.get(
        "JOBS_SOURCE",
        "postgres" if (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")) else "csv",
    )

    return {
        "status": "ok",
        "jobsLoaded": len(jobs_service.load_jobs_once()),
        "jobsPrepared": jobs_service.PROCESSED_JOBS_CACHE is not None,
        "jobsSource": jobs_source,
        "jobsTable": os.environ.get("JOBS_TABLE", "jobs") if jobs_source.lower() != "csv" else None,
        "semanticEngine": "rule-based-bm25-token-cosine",
    }
