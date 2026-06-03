import json
import logging
import math
import re
import threading
from collections import Counter

from modules.config import DATASET_PATH, PROCESSED_JOBS_CACHE_PATH
from modules.data_loader import load_jobs
from modules.nlp import NLP_CACHE_VERSION, SOFT_SKILLS, clean_text, extract_skills, infer_job_domains


logger = logging.getLogger("jobfit.jobs")

JOBS_CACHE = None
PROCESSED_JOBS_CACHE = None
PROCESSED_JOBS_LOCK = threading.Lock()
CORPUS_IDF = {}
CORPUS_AVG_LENGTH = 1.0

MANDATORY_MARKERS = {
    "required", "requirement", "requirements", "wajib", "harus", "must", "minimal",
    "minimum", "min", "dibutuhkan", "menguasai", "memiliki", "able to", "mampu",
    "qualification", "qualifications", "kualifikasi",
}
NICE_TO_HAVE_MARKERS = {
    "preferred", "plus", "nilai tambah", "diutamakan", "nice to have", "bonus",
    "lebih disukai", "preferable", "advantage",
}


def infer_requirement_seniority(title, description):
    text = clean_text(f"{title}. {description[:900]}")
    if any(token in text for token in ("lead", "head", "manager", "supervisor", "senior manager")):
        return "senior_manager"
    if any(token in text for token in ("senior", "sr.", "minimal 5 tahun", "5 tahun", "7 tahun")):
        return "senior"
    if any(token in text for token in ("mid", "middle", "minimal 3 tahun", "3 tahun", "4 tahun")):
        return "mid_level"
    if any(token in text for token in ("junior", "fresh graduate", "entry level", "entry-level")):
        return "junior"
    return "entry_level"


def split_requirement_sentences(text):
    return [
        clean_text(part)
        for part in re.split(r"[\n\r.;•\-\u2022]+", str(text or ""))
        if clean_text(part)
    ]


def parse_job_requirements(title, keyword, description, job_skills, job_domains):
    title_keyword = clean_text(f"{title}. {keyword}")
    sentences = split_requirement_sentences(description)
    mandatory = []
    nice_to_have = []
    soft = []

    for skill in job_skills:
        if skill in SOFT_SKILLS:
            soft.append(skill)
            continue

        skill_text = clean_text(skill)
        matching_sentences = [
            sentence for sentence in sentences
            if f" {skill_text} " in f" {sentence} "
        ]
        is_title_keyword = f" {skill_text} " in f" {title_keyword} "
        is_mandatory = is_title_keyword or any(
            any(marker in sentence for marker in MANDATORY_MARKERS)
            for sentence in matching_sentences
        )
        is_nice = any(
            any(marker in sentence for marker in NICE_TO_HAVE_MARKERS)
            for sentence in matching_sentences
        )

        if is_mandatory and not is_nice:
            mandatory.append(skill)
        else:
            nice_to_have.append(skill)

    if not mandatory:
        technical = [skill for skill in job_skills if skill not in SOFT_SKILLS]
        mandatory = technical[: min(5, len(technical))]
        nice_to_have = [skill for skill in nice_to_have if skill not in set(mandatory)]

    return {
        "mandatorySkills": mandatory[:8],
        "niceToHaveSkills": nice_to_have[:10],
        "softSkills": soft[:8],
        "domainRequirements": list(job_domains or [])[:6],
        "seniorityRequirement": infer_requirement_seniority(title, description),
    }


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
    # Indonesian recruitment-specific words
    "lulusan", "pria", "wanita", "melamar", "berpengalaman", "ditempatkan",
    "penempatan", "keahlian", "kemampuan", "kandidat", "pelamar", "kriteria",
    "persyaratan", "lowongan", "pekerjaan",
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
            build_corpus_stats(PROCESSED_JOBS_CACHE)
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
            job_skills = extract_skills(job_text, fuzzy=False)
            job_domains = infer_job_domains(f"{title}. {keyword}. {description[:1200]}")
            requirements = parse_job_requirements(title, keyword, description, job_skills, job_domains)

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
                    **requirements,
                    "searchText": clean_text(job_text),
                    "titleTokens": token_set(title),
                    "keywordTokens": token_set(keyword),
                    "descriptionTokens": token_set(description[:1200]),
                    "requirementTokens": token_set(f"{title}. {keyword}. {description[:1800]}"),
                    "corpusTokens": tokenize(f"{title}. {keyword}. {description[:1800]}"),
                }
            )

        PROCESSED_JOBS_CACHE = processed_jobs
        build_corpus_stats(PROCESSED_JOBS_CACHE)
        save_processed_jobs_cache(processed_jobs)
        logger.info("Prepared %s processed jobs.", len(processed_jobs))
        return PROCESSED_JOBS_CACHE


def build_corpus_stats(processed_jobs):
    global CORPUS_IDF, CORPUS_AVG_LENGTH

    docs = [list(job.get("corpusTokens") or tokenize(job.get("jobText", ""))) for job in processed_jobs]
    total_docs = len(docs) or 1
    CORPUS_AVG_LENGTH = sum(len(doc) for doc in docs) / total_docs or 1.0
    doc_freq = Counter()

    for doc in docs:
        doc_freq.update(set(doc))

    CORPUS_IDF = {
        token: math.log(1 + ((total_docs - freq + 0.5) / (freq + 0.5)))
        for token, freq in doc_freq.items()
    }


def corpus_relevance_score(query_text, job):
    query_tokens = tokenize(query_text)
    doc_tokens = list(job.get("corpusTokens") or tokenize(job.get("jobText", "")))

    if not query_tokens or not doc_tokens:
        return 0.0

    counts = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    k1 = 1.35
    b = 0.72
    score = 0.0

    for token in set(query_tokens):
        frequency = counts.get(token, 0)
        if not frequency:
            continue

        idf = CORPUS_IDF.get(token, math.log(1 + len(CORPUS_IDF)))
        denominator = frequency + k1 * (1 - b + b * (doc_len / CORPUS_AVG_LENGTH))
        score += idf * ((frequency * (k1 + 1)) / denominator)

    return max(0.0, min(1.0, score / (score + 8.0)))


def serialize_processed_job(job):
    serialized = dict(job)
    serialized["jobSkillSet"] = sorted(job["jobSkillSet"])
    serialized["titleTokens"] = sorted(job["titleTokens"])
    serialized["keywordTokens"] = sorted(job["keywordTokens"])
    serialized["descriptionTokens"] = sorted(job["descriptionTokens"])
    serialized["requirementTokens"] = sorted(job.get("requirementTokens", []))
    serialized["corpusTokens"] = list(job.get("corpusTokens", []))
    serialized["mandatorySkills"] = list(job.get("mandatorySkills", []))
    serialized["niceToHaveSkills"] = list(job.get("niceToHaveSkills", []))
    serialized["softSkills"] = list(job.get("softSkills", []))
    serialized["domainRequirements"] = list(job.get("domainRequirements", []))
    serialized["seniorityRequirement"] = job.get("seniorityRequirement", "entry_level")
    return serialized


def hydrate_processed_job(job):
    hydrated = dict(job)
    hydrated["jobSkillSet"] = set(job.get("jobSkillSet", []))
    hydrated["titleTokens"] = set(job.get("titleTokens", []))
    hydrated["keywordTokens"] = set(job.get("keywordTokens", []))
    hydrated["descriptionTokens"] = set(job.get("descriptionTokens", []))
    hydrated["requirementTokens"] = set(job.get("requirementTokens", []))
    hydrated["corpusTokens"] = list(job.get("corpusTokens", []))
    hydrated["mandatorySkills"] = list(job.get("mandatorySkills", []))
    hydrated["niceToHaveSkills"] = list(job.get("niceToHaveSkills", []))
    hydrated["softSkills"] = list(job.get("softSkills", []))
    hydrated["domainRequirements"] = list(job.get("domainRequirements", []))
    hydrated["seniorityRequirement"] = job.get("seniorityRequirement", "entry_level")
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
