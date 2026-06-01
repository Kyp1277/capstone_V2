import logging
import os

from modules.config import HOST, PORT

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from modules import config, database
from modules.jobs_service import load_jobs_once
from routes.analyses import create_analysis, get_analysis, list_analyses, router as analyses_router
from routes.auth import (
    change_password,
    login,
    logout,
    me,
    register,
    resend_otp,
    router as auth_router,
    update_profile,
    verify_otp,
)
from routes.health import health, router as health_router

# Compatibility exports for local contract tests and older scripts.
from modules.analysis_service import (  # noqa: F401,E402
    analyze_cv_file,
    build_gap_reason,
    build_improvements,
    build_job_improvements,
    build_match_reason,
    build_summary,
    calculate_final_score,
    candidate_prefilter_score,
    cosine_token_score,
    education_match_score,
    get_match_level,
    get_semantic_model,
    overlap_score,
    role_match_score,
    select_candidate_jobs,
    semantic_similarity,
    skill_match_score,
    token_overlap_ratio,
    token_set,
    tokenize,
    transferable_score,
)
from modules.auth_service import (  # noqa: F401,E402
    auth_response,
    bearer_token,
    build_otp_response,
    current_user_from_header,
    is_development,
    issue_register_otp,
    optional_authenticated_user,
    require_authenticated_user,
    send_otp_email,
    smtp_settings,
    validate_auth_payload,
)
from modules.config import (  # noqa: F401,E402
    APP_ENV,
    DATASET_PATH,
    MAX_CANDIDATE_JOBS,
    MAX_UPLOAD_SIZE,
    MIN_EXTRACTED_TEXT_LENGTH,
    PROCESSED_JOBS_CACHE_PATH,
    ROOT,
    TOP_K,
)
from modules.cv_parser import extract_text_from_pdf  # noqa: F401,E402
from modules.jobs_service import (  # noqa: F401,E402
    JOBS_CACHE,
    PROCESSED_JOBS_CACHE,
    get_jobs_cache_signature,
    hydrate_processed_job,
    load_processed_jobs_cache,
    normalize_company,
    normalize_location,
    prepare_jobs_once,
    save_processed_jobs_cache,
    serialize_processed_job,
)
from modules.nlp import clean_text, infer_job_domains  # noqa: F401,E402
from modules.rate_limit import enforce_rate_limit, rate_limit_key  # noqa: F401,E402


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("jobfit.api")

app = FastAPI(
    title="JobFit AI API",
    version="1.0.0",
    description="API untuk parsing CV, skill extraction, match score, missing skills, dan job recommendation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
    return response


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(analyses_router)


@app.on_event("startup")
def startup_event():
    config.validate_production_config()
    try:
        database.ensure_database_schema()
        database.cleanup_expired_records()
    except Exception:
        logger.exception("Database schema setup failed.")
    load_jobs_once()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host=HOST, port=PORT, reload=False)
