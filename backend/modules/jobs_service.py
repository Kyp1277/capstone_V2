import json
import logging
import threading

from modules.config import DATASET_PATH, PROCESSED_JOBS_CACHE_PATH
from modules.data_loader import load_jobs
from modules.nlp import NLP_CACHE_VERSION, clean_text, extract_skills, infer_job_domains


logger = logging.getLogger("jobfit.jobs")

JOBS_CACHE = None
PROCESSED_JOBS_CACHE = None
PROCESSED_JOBS_LOCK = threading.Lock()


STOPWORDS = {
    # Indonesian common words
    "dan", "atau", "yang", "untuk", "dengan", "dalam", "pada", "sebagai",
    "ini", "itu", "ada", "bisa", "juga", "harus", "akan", "sudah", "belum",
    "dari", "ke", "di", "oleh", "agar", "serta", "namun", "jika", "bila",
    "karena", "sehingga", "sesuai", "antara", "setiap", "semua", "secara",
    "selama", "setelah", "sebelum", "melalui", "terhadap", "tentang",
    "bagi", "buat", "memiliki", "melakukan", "dapat", "perlu",
    "wajib", "minimal", "maksimal", "lebih", "sangat", "cukup", "baik",
    "mampu", "mau", "ingin", "saat", "ketika", "pernah", "sedang",
    # English common words
    "the", "and", "for", "with", "role", "position", "job", "staff",
    "junior", "senior", "that", "this", "are", "was", "were", "have",
    "has", "had", "will", "would", "can", "could", "should", "shall",
    "may", "might", "not", "but", "also", "our", "your", "their", "its",
    "you", "they", "them", "into", "from", "about", "over", "such", "any",
    "all", "more", "able", "good", "well", "work", "team", "other",
    "must", "need", "new", "make", "use", "used", "using", "based",
}


def load_jobs_once():
    global JOBS_CACHE
    if JOBS_CACHE is None:
        logger.info("Loading jobs dataset.")
        JOBS_CACHE = load_jobs(DATASET_PATH)
        logger.info("Loaded %s jobs.", len(JOBS_CACHE))
    return JOBS_CACHE


def tokenize(text):
    cleaned = clean_text(text)
    return [
        token
        for token in cleaned.split()
        if len(token) > 2 and token not in STOPWORDS
    ]


def token_set(text):
    return set(tokenize(text))


def normalize_company(value):
    value = str(value or "").strip()
    return value if value and value.lower() != "unknown" else "Perusahaan tidak tersedia"


def normalize_location(value):
    value = str(value or "").strip()
    return value if value and value.lower() != "unknown" else "Lokasi tidak tersedia"


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
                    "titleTokens": token_set(title),
                    "keywordTokens": token_set(keyword),
                    "descriptionTokens": token_set(description[:1200]),
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
