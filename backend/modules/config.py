from pathlib import Path
import os
import sys

from modules.env_loader import load_env_file


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGES = ROOT.parent / ".codex-python-packages"

if LOCAL_PACKAGES.exists() and str(LOCAL_PACKAGES) not in sys.path:
    sys.path.append(str(LOCAL_PACKAGES))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_env_file(ROOT / ".env")


def _env_int(name, default):
    value = os.environ.get(name, str(default)).strip()
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} harus berupa angka.") from error


def parse_csv_env(name):
    return [
        item.strip().rstrip("/")
        for item in os.environ.get(name, "").split(",")
        if item.strip()
    ]


def current_app_env():
    return os.environ.get("APP_ENV", "development").strip().lower()


def is_development():
    return current_app_env() in {"dev", "development", "local", "test"}


def is_production():
    return current_app_env() in {"prod", "production"}


def cors_origins():
    if is_production():
        return parse_csv_env("FRONTEND_ORIGINS")
    return ["*"]


def production_config_errors():
    if not is_production():
        return []

    errors = []
    if not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")):
        errors.append("DATABASE_URL atau POSTGRES_URL wajib diisi.")

    origins = parse_csv_env("FRONTEND_ORIGINS")
    if any(origin == "*" for origin in origins):
        errors.append("FRONTEND_ORIGINS tidak boleh berisi wildcard '*'.")

    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_from = os.environ.get("SMTP_FROM", "").strip()
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    if not smtp_host:
        errors.append("SMTP_HOST wajib diisi agar OTP production bisa dikirim.")
    if not (smtp_from or smtp_user):
        errors.append("SMTP_FROM atau SMTP_USER wajib diisi untuk pengirim OTP.")
    if smtp_user and not smtp_password:
        errors.append("SMTP_PASSWORD wajib diisi jika SMTP_USER digunakan.")

    return errors


def validate_production_config():
    errors = production_config_errors()
    if errors:
        details = " ".join(errors)
        raise RuntimeError(f"Konfigurasi production belum aman. {details}")


DATASET_PATH = ROOT / "data" / "jobs_clean.csv"
PROCESSED_JOBS_CACHE_PATH = ROOT / "data" / "processed_jobs_cache.json"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = _env_int("PORT", 5000)
MAX_UPLOAD_SIZE = _env_int("MAX_UPLOAD_SIZE", 5 * 1024 * 1024)
TOP_K = _env_int("TOP_K", 5)
MAX_CANDIDATE_JOBS = _env_int("MAX_CANDIDATE_JOBS", 250)
MIN_EXTRACTED_TEXT_LENGTH = _env_int("MIN_EXTRACTED_TEXT_LENGTH", 80)
APP_ENV = current_app_env()
FRONTEND_ORIGINS = parse_csv_env("FRONTEND_ORIGINS")
