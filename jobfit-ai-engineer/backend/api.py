from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
import importlib.util
import json
import math
import os
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
LOCAL_PACKAGES = ROOT.parent / ".codex-python-packages"
if LOCAL_PACKAGES.exists():
    sys.path.insert(0, str(LOCAL_PACKAGES))
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from modules.cv_parser import extract_text_from_pdf
from modules.data_loader import load_jobs
from modules.env_loader import load_env_file
from modules.nlp import (
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

DATASET_PATH = ROOT / "data" / "jobs_clean.csv"
PROCESSED_JOBS_CACHE_PATH = ROOT / "data" / "processed_jobs_cache.json"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
TOP_K = int(os.environ.get("TOP_K", "5"))
MAX_CANDIDATE_JOBS = int(os.environ.get("MAX_CANDIDATE_JOBS", "250"))
MIN_EXTRACTED_TEXT_LENGTH = int(os.environ.get("MIN_EXTRACTED_TEXT_LENGTH", "80"))

JOBS_CACHE = None
PROCESSED_JOBS_CACHE = None
PROCESSED_JOBS_LOCK = threading.Lock()
SEMANTIC_MODEL = None
SEMANTIC_LOAD_FAILED = False

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
        JOBS_CACHE = load_jobs(DATASET_PATH)
    return JOBS_CACHE


def prepare_jobs_once():
    global PROCESSED_JOBS_CACHE
    if PROCESSED_JOBS_CACHE is not None:
        return PROCESSED_JOBS_CACHE

    with PROCESSED_JOBS_LOCK:
        if PROCESSED_JOBS_CACHE is not None:
            return PROCESSED_JOBS_CACHE

        cached_jobs = load_processed_jobs_cache()
        if cached_jobs:
            PROCESSED_JOBS_CACHE = cached_jobs
            return PROCESSED_JOBS_CACHE

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
        return {"count": 0, "first": "", "last": ""}

    first = str(jobs[0].get("fingerprint") or jobs[0].get("job_no") or "")
    last = str(jobs[-1].get("fingerprint") or jobs[-1].get("job_no") or "")
    return {"count": len(jobs), "first": first, "last": last}


def load_processed_jobs_cache():
    if not PROCESSED_JOBS_CACHE_PATH.exists():
        return None

    try:
        payload = json.loads(PROCESSED_JOBS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    if payload.get("signature") != get_jobs_cache_signature():
        return None

    return [hydrate_processed_job(job) for job in payload.get("jobs", [])]


def save_processed_jobs_cache(processed_jobs):
    payload = {
        "signature": get_jobs_cache_signature(),
        "jobs": [serialize_processed_job(job) for job in processed_jobs],
    }

    try:
        PROCESSED_JOBS_CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass


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
            "missingSkills": [],
            "improvements": build_improvements([], []),
            "jobs": [],
            "warnings": ["PDF tidak menghasilkan teks yang cukup. Gunakan PDF teks, bukan scan gambar, atau tambahkan OCR."],
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
    }


@app.on_event("startup")
def startup_event():
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


@app.post("/api/analyses")
async def create_analysis(
    cv: UploadFile = File(...),
    targetRole: Optional[str] = Form(None),
    analysisMode: str = Form("targeted"),
):
    mode = analysisMode.strip().lower()
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

        return analyze_cv_file(temp_path, target_role, mode)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Analisis gagal: {error}") from error
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host=HOST, port=PORT, reload=False)
