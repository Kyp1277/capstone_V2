from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
from email.message import EmailMessage
import importlib.util
import json
import logging
import math
import os
import smtplib
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
LOCAL_PACKAGES = ROOT.parent / ".codex-python-packages"
if LOCAL_PACKAGES.exists():
    sys.path.insert(0, str(LOCAL_PACKAGES))
sys.path.insert(0, str(ROOT))

from fastapi import Body, File, Form, Header, HTTPException, UploadFile
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.cv_parser import extract_text_from_pdf
from modules.data_loader import load_jobs
from modules import database
from modules.env_loader import load_env_file
from modules.nlp import (
    NLP_CACHE_VERSION,
    clean_text,
    extract_education_profile,
    extract_skills,
    extract_weighted_skills,
    extract_work_experience,
    calculate_total_experience_years,
    get_experience_level_match,
    infer_job_domains,
)

load_env_file(ROOT / ".env")

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("jobfit.api")

DATASET_PATH = ROOT / "data" / "jobs_clean.csv"
PROCESSED_JOBS_CACHE_PATH = ROOT / "data" / "processed_jobs_cache.json"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
TOP_K = int(os.environ.get("TOP_K", "5"))
MAX_CANDIDATE_JOBS = int(os.environ.get("MAX_CANDIDATE_JOBS", "250"))
MIN_EXTRACTED_TEXT_LENGTH = int(os.environ.get("MIN_EXTRACTED_TEXT_LENGTH", "80"))
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()

JOBS_CACHE = None
PROCESSED_JOBS_CACHE = None
PROCESSED_JOBS_LOCK = threading.Lock()
SEMANTIC_MODEL = None
SEMANTIC_LOAD_FAILED = False
RATE_LIMIT_BUCKETS = {}
RATE_LIMIT_LOCK = threading.Lock()

STOPWORDS = {
    "dan",
    "atau",
    "yang",
    "untuk",
    "dengan",
    "dalam",
    "pada",
    "sebagai",
    "the",
    "and",
    "for",
    "with",
    "role",
    "position",
    "job",
    "staff",
    "junior",
    "senior",
}

app = FastAPI(
    title="JobFit AI API",
    version="1.0.0",
    description="API untuk parsing CV, skill extraction, match score, missing skills, dan job recommendation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_jobs_once():
    global JOBS_CACHE
    if JOBS_CACHE is None:
        logger.info("Loading jobs dataset.")
        JOBS_CACHE = load_jobs(DATASET_PATH)
        logger.info("Loaded %s jobs.", len(JOBS_CACHE))
    return JOBS_CACHE


def bearer_token(authorization):
    if not authorization or not isinstance(authorization, str):
        return ""

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return ""

    return authorization[len(prefix) :].strip()


def current_user_from_header(authorization):
    token = bearer_token(authorization)
    if not token:
        return None

    try:
        return database.get_user_by_token(token)
    except Exception:
        logger.exception("Failed to load authenticated user.")
        return None


def require_authenticated_user(authorization):
    user = current_user_from_header(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sesi login tidak valid. Silakan masuk ulang.")
    return user


def validate_auth_payload(payload, require_name=False):
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    name = str(payload.get("name") or "").strip()

    if require_name and len(name) < 2:
        raise HTTPException(status_code=400, detail="Nama wajib diisi minimal 2 karakter.")

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Masukkan alamat email yang valid.")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password minimal 6 karakter.")

    return {"name": name, "email": email, "password": password}


def auth_response(user):
    token, expires_at = database.create_session(user["id"])
    return {
        "token": token,
        "expiresAt": expires_at.isoformat(),
        "user": user,
    }


def is_development():
    return APP_ENV in {"dev", "development", "local", "test"}


def rate_limit_key(scope, identifier):
    return f"{scope}:{str(identifier or 'anonymous').strip().lower() or 'anonymous'}"


def enforce_rate_limit(scope, identifier, limit=10, window_seconds=60):
    now = time.time()
    key = rate_limit_key(scope, identifier)

    with RATE_LIMIT_LOCK:
        attempts = [
            timestamp
            for timestamp in RATE_LIMIT_BUCKETS.get(key, [])
            if now - timestamp < window_seconds
        ]
        if len(attempts) >= limit:
            RATE_LIMIT_BUCKETS[key] = attempts
            raise HTTPException(
                status_code=429,
                detail="Terlalu banyak percobaan. Tunggu sebentar lalu coba lagi.",
            )
        attempts.append(now)
        RATE_LIMIT_BUCKETS[key] = attempts


def smtp_settings():
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587") or "587"),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from": os.environ.get("SMTP_FROM", "").strip() or os.environ.get("SMTP_USER", "").strip(),
        "tls": os.environ.get("SMTP_TLS", "true").strip().lower() not in {"0", "false", "no"},
    }


def send_otp_email(email, otp):
    settings = smtp_settings()
    if not settings["host"] or not settings["from"]:
        raise RuntimeError("SMTP belum dikonfigurasi.")

    message = EmailMessage()
    message["Subject"] = "Kode Verifikasi JobFit"
    message["From"] = settings["from"]
    message["To"] = email
    message.set_content(
        "Kode verifikasi JobFit Anda adalah:\n\n"
        f"{otp}\n\n"
        "Kode ini berlaku selama 10 menit. Abaikan email ini jika Anda tidak membuat akun JobFit."
    )
    message.add_alternative(
        f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,sans-serif;color:#111827;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f7fb;padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:28px 28px 10px;">
                <h1 style="margin:0;font-size:24px;line-height:1.3;color:#111827;">Kode Verifikasi JobFit</h1>
                <p style="margin:12px 0 0;font-size:15px;line-height:1.6;color:#4b5563;">
                  Gunakan kode berikut untuk menyelesaikan pendaftaran akun JobFit Anda.
                </p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:18px 28px;">
                <div style="display:inline-block;padding:16px 28px;border-radius:14px;background:#eef2ff;color:#1e3a8a;font-size:34px;font-weight:800;letter-spacing:6px;">
                  {otp}
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 28px;">
                <p style="margin:0;font-size:14px;line-height:1.6;color:#4b5563;">
                  Kode ini berlaku selama <strong>10 menit</strong>. Jika Anda tidak membuat akun JobFit, abaikan email ini.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""",
        subtype="html",
    )

    with smtplib.SMTP(settings["host"], settings["port"], timeout=15) as smtp:
        if settings["tls"]:
            smtp.starttls()
        if settings["user"] and settings["password"]:
            smtp.login(settings["user"], settings["password"])
        smtp.send_message(message)


def build_otp_response(otp_payload, otp_sent):
    response = {
        "verificationId": otp_payload["verificationId"],
        "email": otp_payload["email"],
        "expiresAt": otp_payload["expiresAt"],
        "otpSent": otp_sent,
    }
    if is_development() and not otp_sent:
        response["devOtp"] = otp_payload["otp"]
    return response


def issue_register_otp(user):
    otp_payload = database.create_email_otp(user["id"], user["email"])
    try:
        send_otp_email(otp_payload["email"], otp_payload["otp"])
        return build_otp_response(otp_payload, True)
    except Exception as error:
        if is_development():
            logger.warning("OTP email delivery failed; using development fallback: %s", error)
            return build_otp_response(otp_payload, False)
        logger.exception("OTP email delivery failed.")
        raise HTTPException(status_code=500, detail="Email OTP tidak terkirim. Coba beberapa saat lagi.") from error


def prepare_jobs_once():
    global PROCESSED_JOBS_CACHE
    if PROCESSED_JOBS_CACHE is not None:
        return PROCESSED_JOBS_CACHE

    with PROCESSED_JOBS_LOCK:
        if PROCESSED_JOBS_CACHE is not None:
            return PROCESSED_JOBS_CACHE

        cached_jobs = load_processed_jobs_cache()
        if cached_jobs:
            logger.info("Loaded %s processed jobs from cache.", len(cached_jobs))
            PROCESSED_JOBS_CACHE = cached_jobs
            return PROCESSED_JOBS_CACHE

        logger.info("Preparing processed jobs cache.")
        processed_jobs = []
        for job in load_jobs_once():
            title = str(job.get("title", "Unknown"))
            company = normalize_company(job.get("company", "Unknown"))
            location = normalize_location(job.get("location", "Unknown"))
            description = str(job.get("description", ""))
            keyword = str(job.get("keyword", ""))
            job_text = f"{title}. {description}"
            job_skills = extract_skills(job_text)
            job_domains = infer_job_domains(f"{title}. {keyword}. {description[:1200]}")
            title_tokens = token_set(title)
            keyword_tokens = token_set(keyword)
            description_tokens = token_set(description[:1200])

            processed_jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "keyword": keyword,
                    "description": description,
                    "jobText": job_text,
                    "jobSkills": job_skills,
                    "jobSkillSet": set(job_skills),
                    "jobDomains": job_domains,
                    "searchText": clean_text(job_text),
                    "titleTokens": title_tokens,
                    "keywordTokens": keyword_tokens,
                    "descriptionTokens": description_tokens,
                }
            )

        PROCESSED_JOBS_CACHE = processed_jobs
        save_processed_jobs_cache(processed_jobs)
        logger.info("Prepared %s processed jobs.", len(processed_jobs))
        return PROCESSED_JOBS_CACHE


def serialize_processed_job(job):
    serialized = dict(job)
    serialized["jobSkillSet"] = sorted(job["jobSkillSet"])
    serialized["titleTokens"] = sorted(job["titleTokens"])
    serialized["keywordTokens"] = sorted(job["keywordTokens"])
    serialized["descriptionTokens"] = sorted(job["descriptionTokens"])
    return serialized


def hydrate_processed_job(job):
    hydrated = dict(job)
    hydrated["jobSkillSet"] = set(job.get("jobSkillSet", []))
    hydrated["titleTokens"] = set(job.get("titleTokens", []))
    hydrated["keywordTokens"] = set(job.get("keywordTokens", []))
    hydrated["descriptionTokens"] = set(job.get("descriptionTokens", []))
    return hydrated


def get_jobs_cache_signature():
    jobs = load_jobs_once()
    if not jobs:
        return {"count": 0, "first": "", "last": "", "nlpVersion": NLP_CACHE_VERSION}

    first = str(jobs[0].get("fingerprint") or jobs[0].get("job_no") or "")
    last = str(jobs[-1].get("fingerprint") or jobs[-1].get("job_no") or "")
    return {
        "count": len(jobs),
        "first": first,
        "last": last,
        "nlpVersion": NLP_CACHE_VERSION,
    }


def load_processed_jobs_cache():
    if not PROCESSED_JOBS_CACHE_PATH.exists():
        return None

    try:
        payload = json.loads(PROCESSED_JOBS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read processed jobs cache.")
        return None

    if payload.get("signature") != get_jobs_cache_signature():
        logger.info("Processed jobs cache signature mismatch; rebuilding cache.")
        return None

    try:
        return [hydrate_processed_job(job) for job in payload.get("jobs", [])]
    except Exception:
        logger.exception("Failed to hydrate processed jobs cache.")
        return None


def save_processed_jobs_cache(processed_jobs):
    payload = {
        "signature": get_jobs_cache_signature(),
        "jobs": [serialize_processed_job(job) for job in processed_jobs],
    }

    try:
        PROCESSED_JOBS_CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        logger.exception("Failed to write processed jobs cache.")


def get_match_level(score):
    if score >= 80:
        return "Kecocokan Sangat Tinggi"
    if score >= 60:
        return "Kecocokan Tinggi"
    if score >= 40:
        return "Kecocokan Sedang"
    if score >= 20:
        return "Kecocokan Rendah"
    return "Kecocokan Sangat Rendah"


def tokenize(text):
    cleaned = clean_text(text)
    return [
        token
        for token in cleaned.split()
        if len(token) > 2 and token not in STOPWORDS
    ]


def token_set(text):
    return set(tokenize(text))


def overlap_score(left, right):
    left_tokens = token_set(left)
    right_tokens = token_set(right)

    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens)


def cosine_token_score(left, right):
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)

    if not left_tokens or not right_tokens:
        return 0.0

    left_counts = {}
    right_counts = {}

    for token in left_tokens:
        left_counts[token] = left_counts.get(token, 0) + 1

    for token in right_tokens:
        right_counts[token] = right_counts.get(token, 0) + 1

    shared = set(left_counts) & set(right_counts)
    dot = sum(left_counts[token] * right_counts[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (left_norm * right_norm)


def get_semantic_model():
    global SEMANTIC_MODEL, SEMANTIC_LOAD_FAILED

    if SEMANTIC_MODEL is not None or SEMANTIC_LOAD_FAILED:
        return SEMANTIC_MODEL

    try:
        from sentence_transformers import SentenceTransformer

        SEMANTIC_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception:
        logger.info("sentence-transformers unavailable; using token cosine semantic fallback.")
        SEMANTIC_LOAD_FAILED = True
        SEMANTIC_MODEL = None

    return SEMANTIC_MODEL


def semantic_similarity(left, right):
    model = get_semantic_model()

    if model is None:
        return cosine_token_score(left, right)

    try:
        embeddings = model.encode([left, right], convert_to_numpy=True)
        left_vec = embeddings[0]
        right_vec = embeddings[1]
        dot = float((left_vec * right_vec).sum())
        left_norm = math.sqrt(float((left_vec * left_vec).sum()))
        right_norm = math.sqrt(float((right_vec * right_vec).sum()))

        if left_norm == 0 or right_norm == 0:
            return 0.0

        return max(0.0, min(1.0, dot / (left_norm * right_norm)))
    except Exception:
        logger.exception("Semantic model scoring failed; using token cosine fallback.")
        return cosine_token_score(left, right)


def skill_match_score(cv_weighted_skills, job_skills):
    if not isinstance(cv_weighted_skills, dict):
        cv_weighted_skills = {skill: 1.0 for skill in cv_weighted_skills}

    cv_set = set(cv_weighted_skills)
    job_set = set(job_skills)

    if not cv_set or not job_set:
        return 0.0

    matched_skills = cv_set & job_set
    matched_weight = sum(cv_weighted_skills.get(skill, 1.0) for skill in matched_skills)
    required_coverage = min(1.0, matched_weight / len(job_set))
    cv_total_weight = sum(cv_weighted_skills.values()) or 1.0
    cv_relevance = matched_weight / cv_total_weight
    return (0.75 * required_coverage) + (0.25 * cv_relevance)


def role_match_score(target_role, title, description):
    title_score = overlap_score(target_role, title)
    description_score = overlap_score(target_role, description[:600])
    return max(title_score, description_score)


def transferable_score(cv_skills, job_text):
    if not cv_skills:
        return 0.0

    return overlap_score(" ".join(cv_skills), job_text)


def education_match_score(education_profile, job_domains):
    cv_domains = set(education_profile.get("domains", []))
    job_domain_set = set(job_domains or [])

    if not cv_domains or not job_domain_set:
        return 0.5

    if cv_domains & job_domain_set:
        return 1.0

    compatible_pairs = {
        ("it", "data_ai"),
        ("data_ai", "it"),
        ("business", "finance"),
        ("finance", "business"),
        ("design", "it"),
    }

    if any((cv_domain, job_domain) in compatible_pairs for cv_domain in cv_domains for job_domain in job_domain_set):
        return 0.7

    return 0.25


def calculate_final_score(skill_score, semantic_score, role_score, transfer_score, education_score, missing_ratio, is_auto_mode=False):
    if is_auto_mode:
        raw_score = (
            (0.45 * skill_score)
            + (0.25 * semantic_score)
            + (0.15 * transfer_score)
            + (0.15 * education_score)
        )
        penalty = min(0.20, missing_ratio * 0.15)
        return max(0.0, min(1.0, raw_score - penalty))

    raw_score = (
        (0.40 * skill_score)
        + (0.20 * role_score)
        + (0.15 * semantic_score)
        + (0.10 * transfer_score)
        + (0.15 * education_score)
    )
    penalty = min(0.20, missing_ratio * 0.20)
    return max(0.0, min(1.0, raw_score - penalty))


def format_education_label(education_profile):
    majors = education_profile.get("majors", [])
    domains = education_profile.get("domains", [])

    if majors:
        return ", ".join(major.title() for major in majors[:3])

    if domains:
        return ", ".join(domain.replace("_", " ").upper() for domain in domains[:3])

    return "belum terdeteksi jelas"


def build_summary(target_role, detected_skills, missing_skills, score, education_profile=None):
    skill_text = ", ".join(detected_skills[:8]) if detected_skills else "belum ada skill yang terbaca jelas"
    missing_text = ", ".join(missing_skills[:5]) if missing_skills else "tidak ada skill gap utama"
    education_text = format_education_label(education_profile or {})

    return (
        f"CV dianalisis untuk target {target_role}. Pendidikan/jurusan terdeteksi: {education_text}. Skill yang terbaca: {skill_text}. "
        f"Match score terbaik {score}% dengan skill gap utama: {missing_text}."
    )


def build_improvements(detected_skills, missing_skills):
    improvements = []

    if not detected_skills:
        improvements.append("Pastikan CV berupa PDF teks, bukan hasil scan gambar, agar skill dapat terbaca.")
    else:
        improvements.append("Tambahkan bukti penggunaan skill pada pengalaman kerja, project, atau portfolio.")

    improvements.append("Tulis pencapaian dengan angka, dampak, tools, dan konteks pekerjaan yang jelas.")

    if missing_skills:
        improvements.append(f"Prioritaskan peningkatan atau penonjolan skill: {', '.join(missing_skills[:5])}.")

    improvements.append("Sesuaikan ringkasan profil CV dengan target pekerjaan yang dipilih.")

    return improvements


def build_match_reason(title, matched_skills, role_score, semantic_score, education_score=None):
    reasons = []

    if matched_skills:
        reasons.append(f"CV memiliki skill yang relevan dengan lowongan {title}: {', '.join(matched_skills[:5])}.")

    if role_score >= 0.55:
        reasons.append("Target pekerjaan cukup dekat dengan judul atau deskripsi lowongan.")
    elif role_score >= 0.25:
        reasons.append("Ada sebagian kesamaan antara target pekerjaan dan kebutuhan lowongan.")

    if semantic_score >= 0.55:
        reasons.append("Konteks isi CV cukup mirip dengan deskripsi pekerjaan.")

    if education_score is not None:
        if education_score >= 0.9:
            reasons.append("Jurusan atau latar pendidikan CV selaras dengan domain pekerjaan.")
        elif education_score >= 0.65:
            reasons.append("Jurusan CV masih cukup dekat dengan domain pekerjaan.")

    if not reasons:
        reasons.append("Kecocokan masih rendah karena sistem belum menemukan hubungan kuat antara CV dan lowongan.")

    return " ".join(reasons)


def build_gap_reason(title, matched_skills, missing_skills, role_score, semantic_score, education_score=None):
    reasons = []

    if missing_skills:
        reasons.append(
            f"Untuk lowongan {title}, tambahkan pengalaman konkret atau proyek yang menunjukkan skill: {', '.join(missing_skills[:6])}."
        )
    elif matched_skills:
        reasons.append(
            f"Tingkatkan penjelasan penggunaan skill {', '.join(matched_skills[:3])} agar lebih sesuai dengan lowongan {title}."
        )

    if role_score < 0.25:
        reasons.append("Target pekerjaan tidak terlalu dekat dengan judul atau deskripsi lowongan.")
    elif role_score < 0.55:
        reasons.append("Perkuat ringkasan atau judul CV agar lebih cocok dengan lowongan ini.")

    if semantic_score < 0.25:
        reasons.append("Konteks pengalaman CV belum banyak menyerupai deskripsi pekerjaan.")
    elif semantic_score < 0.55:
        reasons.append("Gunakan istilah dan konteks yang lebih mirip dengan deskripsi pekerjaan.")

    if education_score is not None and education_score < 0.4:
        reasons.append("Jurusan atau latar pendidikan CV belum terlalu dekat dengan domain pekerjaan ini.")
    elif education_score is not None and education_score < 0.7:
        reasons.append("Tambahkan hubungan antara latar pendidikan dan pekerjaan ini jika relevan.")

    if not reasons:
        reasons.append(
            f"Untuk lowongan {title}, kecocokan sudah cukup baik, tetapi tambahkan bukti pengalaman yang lebih spesifik."
        )

    return " ".join(reasons)


def build_job_improvements(title, matched_skills, missing_skills, role_score, semantic_score, education_score=None):
    improvements = []

    if missing_skills:
        improvements.append(
            f"Tambahkan pengalaman atau proyek yang menunjukkan skill: {', '.join(missing_skills[:5])}."
        )
    elif matched_skills:
        improvements.append(
            f"Perjelas penggunaan skill {', '.join(matched_skills[:3])} dalam konteks pekerjaan atau proyek."
        )

    if role_score < 0.25:
        improvements.append(
            "Sesuaikan judul CV atau ringkasan profil dengan kata kunci lowongan ini."
        )
    elif role_score < 0.55:
        improvements.append(
            "Perkuat kesamaan antara ringkasan profil dan deskripsi pekerjaan."
        )

    if semantic_score < 0.25:
        improvements.append(
            "Gunakan istilah dan konteks yang lebih mirip dengan deskripsi pekerjaan."
        )
    elif semantic_score < 0.55:
        improvements.append(
            "Tambahkan detail yang membuat konteks pengalaman lebih relevan dengan pekerjaan."
        )

    if education_score is not None and education_score < 0.4:
        improvements.append(
            "Jelaskan hubungan antara latar pendidikan dan domain pekerjaan ini."
        )
    elif education_score is not None and education_score < 0.7:
        improvements.append(
            "Pertegas relevansi pendidikan jika memang mendukung lowongan ini."
        )

    if not improvements:
        improvements.append(
            "CV sudah memiliki kecocokan yang baik; tambahkan bukti pengalaman yang lebih spesifik untuk memperkuat posisi."
        )

    return improvements


def normalize_company(value):
    value = str(value or "").strip()
    return value if value and value.lower() != "unknown" else "Perusahaan tidak tersedia"


def normalize_location(value):
    value = str(value or "").strip()
    return value if value and value.lower() != "unknown" else "Lokasi tidak tersedia"


def token_overlap_ratio(left_tokens, right_tokens):
    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens)


def candidate_prefilter_score(job, cv_weighted_skills, target_role, cv_tokens, target_tokens, education_profile, is_auto_mode):
    job_skills = job["jobSkillSet"]
    skill_score = skill_match_score(cv_weighted_skills, job["jobSkills"])
    matched_weight = sum(cv_weighted_skills.get(skill, 1.0) for skill in set(cv_weighted_skills) & job_skills)
    cv_total_weight = sum(cv_weighted_skills.values()) or 1.0
    cv_overlap = matched_weight / cv_total_weight
    transfer_score = token_overlap_ratio(cv_tokens, job["descriptionTokens"])
    education_score = education_match_score(education_profile, job["jobDomains"])
    role_score = 0.0 if is_auto_mode else max(
        token_overlap_ratio(target_tokens, job["titleTokens"]),
        token_overlap_ratio(target_tokens, job["keywordTokens"]),
        token_overlap_ratio(target_tokens, job["descriptionTokens"]),
    )

    return (0.42 * skill_score) + (0.22 * cv_overlap) + (0.12 * transfer_score) + (0.10 * role_score) + (0.14 * education_score)


def select_candidate_jobs(jobs, cv_weighted_skills, target_role, cv_text, education_profile, is_auto_mode):
    cv_tokens = token_set(cv_text[:2500])
    target_tokens = token_set(target_role)
    ranked_jobs = sorted(
        jobs,
        key=lambda job: candidate_prefilter_score(
            job,
            cv_weighted_skills,
            target_role,
            cv_tokens,
            target_tokens,
            education_profile,
            is_auto_mode,
        ),
        reverse=True,
    )

    return ranked_jobs[: min(MAX_CANDIDATE_JOBS, len(ranked_jobs))]


def analyze_cv_file(pdf_path, target_role, analysis_mode="targeted"):
    jobs = prepare_jobs_once()
    cv_text = extract_text_from_pdf(pdf_path)
    cv_text_length = len(cv_text.strip())
    cv_weighted_skills = extract_weighted_skills(cv_text)
    education_profile = extract_education_profile(cv_text)
    work_experiences = extract_work_experience(cv_text)
    total_experience_years = calculate_total_experience_years(work_experiences)
    cv_experience_level = (
        work_experiences[0].get("level", "entry_level") if work_experiences else "entry_level"
    )
    detected_skills = sorted(cv_weighted_skills, key=lambda skill: (-cv_weighted_skills[skill], skill)) or extract_skills(cv_text)
    is_auto_mode = analysis_mode == "auto"
    effective_target = target_role if not is_auto_mode else "Pekerjaan paling cocok dari CV"

    if cv_text_length < MIN_EXTRACTED_TEXT_LENGTH:
        return {
            "id": f"analysis-{int(time.time() * 1000)}",
            "targetRole": effective_target,
            "analysisMode": analysis_mode,
            "date": time.strftime("%d %B %Y"),
            "score": 0,
            "verdict": get_match_level(0),
            "summary": "Teks CV tidak berhasil dibaca. Pastikan file PDF bukan scan gambar.",
            "detectedSkills": [],
            "workExperiences": [],
            "totalExperienceYears": 0,
            "experienceLevel": "entry_level",
            "experienceMatch": 0,
            "missingSkills": [],
            "improvements": build_improvements([], []),
            "jobs": [],
            "warnings": ["PDF tidak menghasilkan teks yang cukup. Gunakan PDF teks, bukan scan gambar, atau tambahkan OCR."],
            "_cvText": cv_text,
        }

    processed_jobs = []
    candidate_jobs = select_candidate_jobs(jobs, cv_weighted_skills, target_role, cv_text, education_profile, is_auto_mode)

    for job in candidate_jobs:
        title = job["title"]
        company = job["company"]
        location = job["location"]
        description = job["description"]
        job_text = job["jobText"]
        job_skills = job["jobSkills"]
        matched_skills = sorted(set(cv_weighted_skills) & set(job_skills))
        missing_job_skills = sorted(set(job_skills) - set(cv_weighted_skills))

        skill_score = skill_match_score(cv_weighted_skills, job_skills)
        semantic_score = semantic_similarity(cv_text[:3000], job_text[:3000])
        role_score = 0.0 if is_auto_mode else role_match_score(target_role, title, description)
        transfer_score = transferable_score(detected_skills, job_text)
        education_score = education_match_score(education_profile, job["jobDomains"])
        missing_ratio = len(missing_job_skills) / len(job_skills) if job_skills else 1.0
        final_score = calculate_final_score(
            skill_score,
            semantic_score,
            role_score,
            transfer_score,
            education_score,
            missing_ratio,
            is_auto_mode,
        )

        processed_jobs.append(
            {
                "title": title.title(),
                "company": company,
                "location": location,
                "skills": job_skills,
                "matchedSkills": matched_skills,
                "missingSkills": missing_job_skills[:10],
                "match": round(final_score * 100),
                "detail": build_match_reason(title, matched_skills, role_score if not is_auto_mode else semantic_score, semantic_score, education_score),
                "notFitReason": build_gap_reason(
                    title,
                    matched_skills,
                    missing_job_skills,
                    role_score if not is_auto_mode else semantic_score,
                    semantic_score,
                    education_score,
                ),
                "improvements": build_job_improvements(
                    title,
                    matched_skills,
                    missing_job_skills,
                    role_score if not is_auto_mode else semantic_score,
                    semantic_score,
                    education_score,
                ),
                "description": description[:220].strip() or "Detail pekerjaan belum tersedia.",
                "scoreBreakdown": {
                    "skillMatch": round(skill_score * 100),
                    "semanticMatch": round(semantic_score * 100),
                    "roleMatch": round(role_score * 100),
                    "contextMatch": round(transfer_score * 100),
                    "educationMatch": round(education_score * 100),
                    "missingSkillPenalty": round(min(20, missing_ratio * 20)),
                },
            }
        )

    processed_jobs.sort(key=lambda item: item["match"], reverse=True)
    top_jobs = processed_jobs[:TOP_K]
    missing_skills = sorted({skill for job in top_jobs for skill in job["missingSkills"]})[:10]
    best_score = top_jobs[0]["match"] if top_jobs else 0
    experience_match_score = round(
        get_experience_level_match(cv_experience_level, top_jobs[0]["title"]) * 100
    ) if top_jobs else 0

    return {
        "id": f"analysis-{int(time.time() * 1000)}",
        "targetRole": effective_target,
        "analysisMode": analysis_mode,
        "date": time.strftime("%d %B %Y"),
        "score": best_score,
        "verdict": get_match_level(best_score),
        "summary": build_summary(target_role, detected_skills, missing_skills, best_score, education_profile),
        "detectedSkills": detected_skills,
        "workExperiences": work_experiences,
        "totalExperienceYears": total_experience_years,
        "experienceLevel": cv_experience_level,
        "experienceMatch": experience_match_score,
        "missingSkills": missing_skills,
        "improvements": build_improvements(detected_skills, missing_skills),
        "jobs": top_jobs,
        "warnings": [],
        "_cvText": cv_text,
    }


@app.on_event("startup")
def startup_event():
    try:
        database.ensure_database_schema()
        database.cleanup_expired_records()
    except Exception:
        logger.exception("Database schema setup failed.")
    load_jobs_once()


@app.get("/health")
def health():
    jobs_source = os.environ.get(
        "JOBS_SOURCE",
        "postgres" if (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")) else "csv",
    )

    return {
        "status": "ok",
        "jobsLoaded": len(load_jobs_once()),
        "jobsPrepared": PROCESSED_JOBS_CACHE is not None,
        "jobsSource": jobs_source,
        "jobsTable": os.environ.get("JOBS_TABLE", "jobs") if jobs_source.lower() != "csv" else None,
        "semanticEngine": (
            "sentence-transformers/all-MiniLM-L6-v2"
            if importlib.util.find_spec("sentence_transformers")
            else "token-cosine-fallback"
        ),
    }


@app.post("/api/auth/register")
def register(payload: dict = Body(...)):
    data = validate_auth_payload(payload, require_name=True)
    enforce_rate_limit("register", data["email"], limit=5, window_seconds=10 * 60)

    try:
        user = database.create_or_update_unverified_user(data["name"], data["email"], data["password"])
        if not user:
            raise HTTPException(status_code=409, detail="Email sudah terdaftar. Silakan masuk dengan akun tersebut.")
        return issue_register_otp(user)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Registration failed.")
        raise HTTPException(status_code=500, detail="Registrasi gagal diproses.") from error


@app.post("/api/auth/verify-otp")
def verify_otp(payload: dict = Body(...)):
    verification_id = str(payload.get("verificationId") or "").strip()
    email = str(payload.get("email") or "").strip().lower()
    otp = str(payload.get("otp") or "").strip()

    if not verification_id or "@" not in email or len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="Kode verifikasi tidak valid.")
    enforce_rate_limit("verify_otp", email, limit=8, window_seconds=10 * 60)

    try:
        result = database.verify_email_otp(verification_id, email, otp)
        if not result["ok"]:
            messages = {
                "not_found": "Kode verifikasi tidak ditemukan.",
                "consumed": "Kode verifikasi sudah digunakan.",
                "expired": "Kode verifikasi sudah kedaluwarsa. Kirim ulang kode.",
                "too_many_attempts": "Terlalu banyak percobaan kode. Kirim ulang kode.",
                "invalid": "Kode verifikasi salah.",
            }
            raise HTTPException(status_code=400, detail=messages.get(result["reason"], "Kode verifikasi tidak valid."))
        return auth_response(result["user"])
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("OTP verification failed.")
        raise HTTPException(status_code=500, detail="Verifikasi OTP gagal diproses.") from error


@app.post("/api/auth/resend-otp")
def resend_otp(payload: dict = Body(...)):
    email = str(payload.get("email") or "").strip().lower()

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Masukkan alamat email yang valid.")
    enforce_rate_limit("resend_otp", email, limit=3, window_seconds=10 * 60)

    try:
        otp_payload, reason = database.create_otp_for_unverified_email(email)
        if reason == "not_found":
            raise HTTPException(status_code=404, detail="Akun belum ditemukan. Silakan daftar ulang.")
        if reason == "verified":
            raise HTTPException(status_code=409, detail="Email sudah diverifikasi. Silakan masuk.")
        try:
            send_otp_email(otp_payload["email"], otp_payload["otp"])
            return build_otp_response(otp_payload, True)
        except Exception as error:
            if is_development():
                logger.warning("OTP resend email delivery failed; using development fallback: %s", error)
                return build_otp_response(otp_payload, False)
            logger.exception("OTP resend email delivery failed.")
            raise HTTPException(status_code=500, detail="Email OTP tidak terkirim. Coba beberapa saat lagi.") from error
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("OTP resend failed.")
        raise HTTPException(status_code=500, detail="Kirim ulang OTP gagal diproses.") from error


@app.post("/api/auth/login")
def login(payload: dict = Body(...)):
    data = validate_auth_payload(payload, require_name=False)
    enforce_rate_limit("login", data["email"], limit=8, window_seconds=10 * 60)

    try:
        user = database.authenticate_user(data["email"], data["password"])
        if not user:
            raise HTTPException(status_code=401, detail="Email atau password tidak cocok.")
        if not user.get("emailVerified"):
            raise HTTPException(status_code=403, detail="Email belum diverifikasi.")

        return auth_response(user)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Login failed.")
        raise HTTPException(status_code=500, detail="Login gagal diproses.") from error


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(None)):
    return {"user": require_authenticated_user(authorization)}


@app.patch("/api/auth/me")
def update_profile(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    user = require_authenticated_user(authorization)
    name = str(payload.get("name") or "").strip()

    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Nama wajib diisi minimal 2 karakter.")

    try:
        return {"user": database.update_user(user["id"], name)}
    except Exception as error:
        logger.exception("Profile update failed.")
        raise HTTPException(status_code=500, detail="Profil gagal diperbarui.") from error


@app.post("/api/auth/change-password")
def change_password(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    user = require_authenticated_user(authorization)
    current_password = str(payload.get("currentPassword") or "")
    new_password = str(payload.get("newPassword") or "")
    confirm_password = str(payload.get("confirmPassword") or "")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password baru minimal 6 karakter.")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Konfirmasi password baru tidak sama.")

    try:
        if not database.change_user_password(user["id"], current_password, new_password):
            raise HTTPException(status_code=400, detail="Password saat ini tidak cocok.")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Password change failed.")
        raise HTTPException(status_code=500, detail="Password gagal diganti.") from error


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    try:
        database.delete_session(bearer_token(authorization))
    except Exception:
        logger.exception("Logout failed.")

    return {"ok": True}


@app.get("/api/analyses")
def list_analyses(authorization: Optional[str] = Header(None)):
    user = require_authenticated_user(authorization)

    try:
        return {"analyses": database.list_user_analyses(user["id"])}
    except Exception as error:
        logger.exception("Failed to list analyses.")
        raise HTTPException(status_code=500, detail="Riwayat analisis gagal dimuat.") from error


@app.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: str, authorization: Optional[str] = Header(None)):
    user = require_authenticated_user(authorization)

    try:
        analysis = database.get_user_analysis(user["id"], analysis_id)
    except Exception as error:
        logger.exception("Failed to load analysis detail.")
        raise HTTPException(status_code=500, detail="Detail analisis gagal dimuat.") from error

    if not analysis:
        raise HTTPException(status_code=404, detail="Hasil analisis tidak ditemukan.")

    return analysis


@app.post("/api/analyses")
async def create_analysis(
    cv: UploadFile = File(...),
    targetRole: Optional[str] = Form(None),
    analysisMode: str = Form("targeted"),
    authorization: Optional[str] = Header(None),
):
    mode = analysisMode.strip().lower()
    token = bearer_token(authorization)
    enforce_rate_limit("analysis", token or "anonymous", limit=8, window_seconds=10 * 60)
    if mode not in {"targeted", "auto"}:
        raise HTTPException(status_code=400, detail="Mode analisis tidak valid.")

    target_role = (targetRole or "").strip()

    if mode == "targeted" and len(target_role) < 3:
        raise HTTPException(status_code=400, detail="Target pekerjaan wajib diisi minimal 3 karakter.")

    filename = cv.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus berformat PDF.")

    content = await cv.read()
    if not content:
        raise HTTPException(status_code=400, detail="File CV kosong.")

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Ukuran file maksimal 5 MB.")

    temp_path: Optional[str] = None

    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        result = analyze_cv_file(temp_path, target_role, mode)
        cv_text = result.pop("_cvText", "")
        user = current_user_from_header(authorization)

        if user:
            try:
                result = database.save_analysis(user["id"], result, cv_text)
            except Exception:
                logger.exception("Failed to persist analysis.")

        return result
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("CV analysis failed.")
        raise HTTPException(status_code=500, detail="Analisis gagal diproses. Coba beberapa saat lagi.") from error
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host=HOST, port=PORT, reload=False)
