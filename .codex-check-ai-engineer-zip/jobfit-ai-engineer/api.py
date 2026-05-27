from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
import importlib.util
import math
import os
import sys
import time

# =========================================
# ROOT PATH
# =========================================
ROOT = Path(__file__).resolve().parent

# supaya import modules bisa kebaca
sys.path.insert(0, str(ROOT))

# =========================================
# FASTAPI
# =========================================
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# =========================================
# MODULE IMPORT
# =========================================
from cv_parser import extract_text_from_pdf
from data_loader import load_jobs
from nlp import clean_text, extract_skills

# =========================================
# CONFIG
# =========================================
DATASET_PATH = ROOT / "data" / "jobs_clean.csv"

HOST = "127.0.0.1"
PORT = 5000

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
TOP_K = 5

# =========================================
# CACHE
# =========================================
JOBS_CACHE = None
SEMANTIC_MODEL = None
SEMANTIC_LOAD_FAILED = False

# =========================================
# STOPWORDS
# =========================================
STOPWORDS = {
    "dan",
    "atau",
    "yang",
    "untuk",
    "dengan",
    "dalam",
    "the",
    "and",
    "for",
    "with",
    "job",
    "staff",
    "junior",
    "senior",
}

# =========================================
# FASTAPI APP
# =========================================
app = FastAPI(
    title="JobFit AI API",
    version="1.0.0"
)

# =========================================
# CORS
# =========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================
# LOAD JOBS
# =========================================
def load_jobs_once():

    global JOBS_CACHE

    if JOBS_CACHE is None:
        JOBS_CACHE = load_jobs(DATASET_PATH)

    return JOBS_CACHE

# =========================================
# MATCH LEVEL
# =========================================
def get_match_level(score):

    if score >= 80:
        return "Excellent Match"

    elif score >= 60:
        return "Strong Match"

    elif score >= 40:
        return "Moderate Match"

    elif score >= 20:
        return "Low Match"

    return "Very Low Match"

# =========================================
# TOKENIZE
# =========================================
def tokenize(text):

    cleaned = clean_text(text)

    return [
        token
        for token in cleaned.split()
        if len(token) > 2 and token not in STOPWORDS
    ]

# =========================================
# OVERLAP SCORE
# =========================================
def overlap_score(left, right):

    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))

    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens)

# =========================================
# FALLBACK COSINE
# =========================================
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

    dot = sum(
        left_counts[token] * right_counts[token]
        for token in shared
    )

    left_norm = math.sqrt(
        sum(v * v for v in left_counts.values())
    )

    right_norm = math.sqrt(
        sum(v * v for v in right_counts.values())
    )

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (left_norm * right_norm)

# =========================================
# LOAD MINI LM V2
# =========================================
def get_semantic_model():

    global SEMANTIC_MODEL
    global SEMANTIC_LOAD_FAILED

    if SEMANTIC_MODEL is not None:
        return SEMANTIC_MODEL

    if SEMANTIC_LOAD_FAILED:
        return None

    try:

        from sentence_transformers import SentenceTransformer

        # MODEL MINI LM V2
        SEMANTIC_MODEL = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        return SEMANTIC_MODEL

    except Exception:

        SEMANTIC_LOAD_FAILED = True
        return None

# =========================================
# SEMANTIC SIMILARITY
# =========================================
def semantic_similarity(text1, text2):

    model = get_semantic_model()

    if model is None:
        return cosine_token_score(text1, text2)

    try:

        embeddings = model.encode(
            [text1, text2],
            convert_to_numpy=True
        )

        emb1 = embeddings[0]
        emb2 = embeddings[1]

        dot = float((emb1 * emb2).sum())

        norm1 = math.sqrt(
            float((emb1 * emb1).sum())
        )

        norm2 = math.sqrt(
            float((emb2 * emb2).sum())
        )

        if norm1 == 0 or norm2 == 0:
            return 0.0

        score = dot / (norm1 * norm2)

        return max(0.0, min(1.0, score))

    except Exception:

        return cosine_token_score(text1, text2)

# =========================================
# SKILL MATCH SCORE
# =========================================
def skill_match_score(cv_skills, job_skills):

    cv_set = set(cv_skills)
    job_set = set(job_skills)

    if not cv_set or not job_set:
        return 0.0

    matched = cv_set & job_set

    return len(matched) / len(job_set)

# =========================================
# ANALYZE CV
# =========================================
def analyze_cv_file(pdf_path):

    jobs = load_jobs_once()

    # =====================================
    # PARSING PDF CV
    # =====================================
    cv_text = extract_text_from_pdf(pdf_path)

    # =====================================
    # NLP SKILL EXTRACTION
    # =====================================
    detected_skills = extract_skills(cv_text)

    # =====================================
    # VALIDASI
    # =====================================
    if not cv_text.strip():

        return {
            "score": 0,
            "verdict": "CV tidak terbaca",
            "skills": [],
            "jobs": []
        }

    processed_jobs = []

    # =====================================
    # PROCESS ALL JOBS
    # =====================================
    for job in jobs:

        title = str(job.get("title", "Unknown"))
        company = str(job.get("company", "Unknown"))
        location = str(job.get("location", "Unknown"))
        description = str(job.get("description", ""))

        # =================================
        # JOB SKILLS
        # =================================
        job_skills = extract_skills(
            f"{title} {description}"
        )

        # =================================
        # SKILL MATCH
        # =================================
        skill_score = skill_match_score(
            detected_skills,
            job_skills
        )

        # =================================
        # SEMANTIC MATCH
        # =================================
        semantic_score = semantic_similarity(
            cv_text[:3000],
            description[:3000]
        )

        # =================================
        # FINAL SCORE
        # =================================
        final_score = (
            (0.7 * skill_score) +
            (0.3 * semantic_score)
        )

        matched_skills = list(
            set(detected_skills) &
            set(job_skills)
        )

        missing_skills = list(
            set(job_skills) -
            set(detected_skills)
        )

        processed_jobs.append({

            "title": title,
            "company": company,
            "location": location,

            "matchScore": round(
                final_score * 100,
                2
            ),

            "matchLevel": get_match_level(
                round(final_score * 100, 2)
            ),

            "matchedSkills": matched_skills[:10],

            "missingSkills": missing_skills[:10],

            "jobSkills": job_skills[:15]
        })

    # =====================================
    # SORT SCORE
    # =====================================
    processed_jobs.sort(
        key=lambda x: x["matchScore"],
        reverse=True
    )

    top_jobs = processed_jobs[:TOP_K]

    best_score = (
        top_jobs[0]["matchScore"]
        if top_jobs else 0
    )

    return {

        "score": best_score,

        "verdict": get_match_level(best_score),

        "detectedSkills": detected_skills,

        "jobs": top_jobs
    }

# =========================================
# HEALTH CHECK
# =========================================
@app.get("/health")
def health():

    return {
        "status": "ok",
        "jobsLoaded": len(load_jobs_once()),
        "semanticModel": "all-MiniLM-L6-v2"
    }

# =========================================
# ANALYSIS API
# =========================================
@app.post("/api/analyze")
async def analyze_cv(
    cv: UploadFile = File(...)
):

    filename = cv.filename or ""

    # =====================================
    # VALIDASI PDF
    # =====================================
    if not filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="File harus PDF"
        )

    content = await cv.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="File kosong"
        )

    if len(content) > MAX_UPLOAD_SIZE:

        raise HTTPException(
            status_code=400,
            detail="Ukuran file terlalu besar"
        )

    temp_path = None

    try:

        # =================================
        # SAVE TEMP PDF
        # =================================
        with NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_file.write(content)
            temp_path = temp_file.name

        # =================================
        # ANALYZE CV
        # =================================
        result = analyze_cv_file(temp_path)

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

# =========================================
# START SERVER
# =========================================
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "api:app",
        host=HOST,
        port=PORT,
        reload=True
    )