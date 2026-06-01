import logging
import math
import time

from modules import jobs_service
from modules.config import MAX_CANDIDATE_JOBS, MIN_EXTRACTED_TEXT_LENGTH, TOP_K
from modules.cv_parser import extract_text_from_pdf
from modules.nlp import (
    calculate_total_experience_years,
    clean_text,
    extract_education_profile,
    extract_skills,
    extract_weighted_skills,
    extract_work_experience,
    get_experience_level_match,
)


logger = logging.getLogger("jobfit.analysis")
SEMANTIC_MODEL = None
SEMANTIC_LOAD_FAILED = False

# K7: Cache for job description embeddings — avoids re-encoding the same
# job descriptions on every request. Key = first 120 chars of job text.
_JOB_EMBEDDING_CACHE: dict = {}

# K14: Semaphore to prevent concurrent requests from all calling model.encode()
# simultaneously, which causes memory pressure on limited-resource servers.
import threading
_SEMANTIC_SEMAPHORE = threading.Semaphore(2)  # max 2 concurrent encode calls

# K2: Preferred model order — more capable multilingual models first.
# Falls back to the original small model if the preferred one is unavailable.
# paraphrase-multilingual-MiniLM-L12-v2 supports 50+ languages including Indonesian
# and is trained on multilingual sentence pairs, making it far better for
# bilingual ID-EN CVs than the English-only all-MiniLM-L6-v2.
_SEMANTIC_MODEL_CANDIDATES = [
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 50+ languages, ~120MB
    "sentence-transformers/all-MiniLM-L6-v2",                       # English fallback, ~22MB
]

TARGET_ROLE_SYNONYMS = {
    "koki": {"cook", "chef", "kitchen", "dapur", "culinary", "kuliner", "memasak", "masak"},
    "juru": {"cook", "chef", "kitchen", "dapur", "culinary"},
    "masak": {"cook", "chef", "kitchen", "dapur", "culinary"},
    "memasak": {"cook", "chef", "kitchen", "dapur", "culinary"},
    "chef": {"koki", "cook", "kitchen", "dapur", "culinary"},
    "cook": {"koki", "chef", "kitchen", "dapur", "culinary"},
    "dapur": {"koki", "cook", "chef", "kitchen", "culinary"},
}


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
    return jobs_service.tokenize(text)


def token_set(text):
    return jobs_service.token_set(text)


def overlap_score(left, right):
    left_tokens = token_set(left)
    right_tokens = token_set(right)

    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens)


def expanded_target_tokens(target_role):
    tokens = token_set(target_role)
    expanded = set(tokens)

    for token in tokens:
        expanded.update(TARGET_ROLE_SYNONYMS.get(token, set()))

    return expanded


def target_role_overlap(target_role, text):
    base_tokens = token_set(target_role)
    right_tokens = token_set(text)

    if not base_tokens or not right_tokens:
        return 0.0

    target_tokens = expanded_target_tokens(target_role)
    return min(1.0, len(target_tokens & right_tokens) / len(base_tokens))


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
    except Exception:
        logger.info("sentence-transformers unavailable; using token cosine semantic fallback.")
        SEMANTIC_LOAD_FAILED = True
        return None

    # K2: Try each candidate model in order — prefer multilingual model
    for model_name in _SEMANTIC_MODEL_CANDIDATES:
        try:
            SEMANTIC_MODEL = SentenceTransformer(model_name)
            logger.info("Loaded semantic model: %s", model_name)
            return SEMANTIC_MODEL
        except Exception:
            logger.warning("Failed to load semantic model %s; trying next candidate.", model_name)

    logger.warning("All semantic model candidates failed; using token cosine fallback.")
    SEMANTIC_LOAD_FAILED = True
    return None


def semantic_similarity(left, right, cache_key=None):
    model = get_semantic_model()

    if model is None:
        return cosine_token_score(left, right)

    # K14: Limit concurrent model.encode() calls to avoid memory pressure
    # on servers with limited resources. Falls back to token cosine if
    # semaphore cannot be acquired within 5 seconds.
    acquired = _SEMANTIC_SEMAPHORE.acquire(timeout=5)
    if not acquired:
        logger.warning("Semantic semaphore timeout; using token cosine fallback.")
        return cosine_token_score(left, right)

    try:
        left_vec = model.encode(left, convert_to_numpy=True)

        # K7: Cache right-side (job) embeddings — only encoded once per unique job
        if cache_key is not None and cache_key in _JOB_EMBEDDING_CACHE:
            right_vec = _JOB_EMBEDDING_CACHE[cache_key]
        else:
            right_vec = model.encode(right, convert_to_numpy=True)
            if cache_key is not None:
                _JOB_EMBEDDING_CACHE[cache_key] = right_vec

        dot = float((left_vec * right_vec).sum())
        left_norm = math.sqrt(float((left_vec * left_vec).sum()))
        right_norm = math.sqrt(float((right_vec * right_vec).sum()))

        if left_norm == 0 or right_norm == 0:
            return 0.0

        return max(0.0, min(1.0, dot / (left_norm * right_norm)))
    except Exception:
        logger.exception("Semantic model scoring failed; using token cosine fallback.")
        return cosine_token_score(left, right)
    finally:
        _SEMANTIC_SEMAPHORE.release()


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
    title_score = target_role_overlap(target_role, title)
    description_score = target_role_overlap(target_role, description[:600])
    return max(title_score, description_score)


def transferable_score(cv_skills, job_text):
    if not cv_skills:
        return 0.0

    return overlap_score(" ".join(cv_skills), job_text)


def education_match_score(education_profile, job_domains):
    cv_domains = set(education_profile.get("domains", []))
    job_domain_set = set(job_domains or [])
    cv_degrees = set(education_profile.get("degrees", []))

    if not cv_domains or not job_domain_set:
        return 0.5

    if "culinary" in job_domain_set and "culinary" not in cv_domains:
        return 0.25

    # K9: Strict check for highly-specific domains
    for strict_domain in ("healthcare", "legal"):
        if strict_domain in job_domain_set and strict_domain not in cv_domains:
            return 0.20

    if cv_domains & job_domain_set:
        base_score = 1.0
        # K9: Adjust based on degree level
        high_degrees = {"s2", "s3", "master", "magister"}
        low_degrees = {"sma", "smk", "d1", "d2"}
        if cv_degrees & high_degrees:
            base_score = min(1.0, base_score + 0.05)
        elif cv_degrees & low_degrees:
            base_score = max(0.6, base_score - 0.15)
        return round(base_score, 2)

    compatible_pairs = {
        ("it", "data_ai"),
        ("data_ai", "it"),
        ("business", "finance"),
        ("finance", "business"),
        ("design", "it"),
        ("logistics", "engineering"),
        ("engineering", "logistics"),
        ("business", "logistics"),
    }

    if any(
        (cv_domain, job_domain) in compatible_pairs
        for cv_domain in cv_domains
        for job_domain in job_domain_set
    ):
        return 0.7

    return 0.25


def calculate_final_score(skill_score, semantic_score, role_score, transfer_score, education_score, missing_ratio, is_auto_mode=False):
    """
    Weighted hybrid scoring formula.

    Targeted mode weights (rationale):
      40% Skill Match     — primary signal; technical overlap is most reliable
      20% Role Match      — ensures job title relevance to user's target
      15% Semantic        — context similarity; conservative weight (small model)
      15% Education Match — domain alignment provides meaningful signal
      10% Transferable    — broad token overlap as weaker supporting signal

    Auto mode (no target role) — role_score removed; semantic gets higher weight:
      45% Skill Match
      25% Semantic
      15% Transferable
      15% Education Match

    Missing skill penalty: capped at 20% to avoid over-penalising partial CVs.
    Role cap: if role_score < 0.05 the job is likely irrelevant; clamp to 0.35.
    """
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
    final_score = max(0.0, min(1.0, raw_score - penalty))
    if role_score < 0.05:
        final_score = min(final_score, 0.35)
    return final_score


def format_education_label(education_profile):
    majors = education_profile.get("majors", [])
    domains = education_profile.get("domains", [])

    if majors:
        return ", ".join(major.title() for major in majors[:3])

    if domains:
        return ", ".join(domain.replace("_", " ").upper() for domain in domains[:3])

    return "belum terdeteksi jelas"


def build_summary(target_role, detected_skills, missing_skills, score, education_profile=None, weighted_skills=None):
    skill_text = ", ".join(detected_skills[:8]) if detected_skills else "belum ada skill yang terbaca jelas"
    missing_text = ", ".join(missing_skills[:5]) if missing_skills else "tidak ada skill gap utama"
    education_text = format_education_label(education_profile or {})

    # K11: Mention top skills by confidence weight
    confidence_note = ""
    if weighted_skills:
        top_confident = sorted(weighted_skills.items(), key=lambda x: -x[1])[:3]
        top_names = ", ".join(sk for sk, _ in top_confident)
        confidence_note = f" Skill paling dominan: {top_names}."

    return (
        f"CV dianalisis untuk target {target_role}. Pendidikan/jurusan terdeteksi: {education_text}. "
        f"Skill yang terbaca: {skill_text}.{confidence_note} "
        f"Match score terbaik {score}% dengan skill gap utama: {missing_text}."
    )


def build_improvements(detected_skills, missing_skills, weighted_skills=None):
    """K12: Generate specific, personalised improvement tips based on actual gaps."""
    improvements = []

    if not detected_skills:
        improvements.append(
            "Pastikan CV berupa PDF teks, bukan hasil scan gambar, agar skill dapat terbaca."
        )
        return improvements

    # K11+K12: Skills detected but with low confidence — suggest strengthening context
    if weighted_skills:
        soft_skill_names = {
            "time management", "problem solving", "teamwork", "collaboration",
            "leadership", "communication", "interpersonal", "effective communication",
        }
        low_confidence = [
            sk for sk, wt in weighted_skills.items()
            if wt < 1.2 and sk not in soft_skill_names
        ]
        if low_confidence:
            improvements.append(
                f"Perkuat konteks penggunaan skill: {', '.join(low_confidence[:4])}. "
                "Cantumkan dalam proyek atau pengalaman kerja agar bobot deteksi lebih tinggi."
            )

    # K12: Specific missing skills
    if missing_skills:
        improvements.append(
            f"Prioritaskan penambahan atau penonjolan skill yang paling dibutuhkan: "
            f"{', '.join(missing_skills[:4])}."
        )

    improvements.append(
        "Tulis pencapaian dengan angka, dampak, tools, dan konteks pekerjaan yang jelas "
        "(contoh: 'Membangun REST API dengan Python yang mengurangi response time 30%')."
    )
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
    role_score = 0.0 if is_auto_mode else role_match_score(target_role, job["title"], job["description"])

    return (0.42 * skill_score) + (0.22 * cv_overlap) + (0.12 * transfer_score) + (0.10 * role_score) + (0.14 * education_score)


def select_candidate_jobs(jobs, cv_weighted_skills, target_role, cv_text, education_profile, is_auto_mode):
    cv_tokens = token_set(cv_text[:2500])
    target_tokens = token_set(target_role)
    candidate_pool = jobs

    if not is_auto_mode:
        role_matched_jobs = [
            job for job in jobs
            if role_match_score(target_role, job["title"], job["description"]) >= 0.25
        ]
        if role_matched_jobs:
            candidate_pool = role_matched_jobs

    ranked_jobs = sorted(
        candidate_pool,
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
    jobs = jobs_service.prepare_jobs_once()
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
            "improvements": build_improvements([], [], None),
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
        job_cache_key = job_text[:120]
        semantic_score = semantic_similarity(cv_text[:3000], job_text[:3000], cache_key=job_cache_key)
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
        "summary": build_summary(target_role, detected_skills, missing_skills, best_score, education_profile, cv_weighted_skills),
        "detectedSkills": detected_skills,
        # K11: Expose per-skill confidence weight for UI display
        "skillConfidence": {
            skill: round(cv_weighted_skills.get(skill, 1.0), 2)
            for skill in detected_skills
        },
        "workExperiences": work_experiences,
        "totalExperienceYears": total_experience_years,
        "experienceLevel": cv_experience_level,
        "experienceMatch": experience_match_score,
        "missingSkills": missing_skills,
        "improvements": build_improvements(detected_skills, missing_skills, cv_weighted_skills),
        "jobs": top_jobs,
        "warnings": [],
        "_cvText": cv_text,
    }
