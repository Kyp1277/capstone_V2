"""
Evaluation smoke test untuk kredibilitas rekomendasi JobFit.

Test ini memakai CV synthetic/anonymized dan in-memory jobs agar bisa
dijalankan tanpa PDF eksternal atau database. Tujuannya memastikan ranking
tidak selalu mengarah ke role IT dan skill utama tetap terdeteksi.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evaluation" / "cases.json"
sys.path.insert(0, str(ROOT))

import api  # noqa: E402
from modules import analysis_service, jobs_service  # noqa: E402


EVAL_JOBS = [
    {
        "title": "Frontend React Developer",
        "company": "Demo",
        "location": "Remote",
        "keyword": "frontend react web javascript",
        "description": "React frontend developer membangun web UI dengan HTML CSS JavaScript REST API Git responsive design testing dan performance optimization.",
    },
    {
        "title": "Backend Python Engineer",
        "company": "Demo",
        "location": "Remote",
        "keyword": "backend python api engineer",
        "description": "Backend engineer menggunakan Python FastAPI PostgreSQL REST API Docker Git unit testing database optimization dan deployment service.",
    },
    {
        "title": "Data Analyst",
        "company": "Demo",
        "location": "Jakarta",
        "keyword": "data analyst business intelligence",
        "description": "Data analyst mengolah SQL Python Excel dashboard data visualization statistics ETL reporting dan business insight.",
    },
    {
        "title": "Junior Web Developer",
        "company": "Demo",
        "location": "Bandung",
        "keyword": "junior developer web software",
        "description": "Junior web developer memakai JavaScript PHP MySQL HTML CSS Git REST API dan problem solving untuk aplikasi web.",
    },
    {
        "title": "Administrative Staff",
        "company": "Demo",
        "location": "Jakarta",
        "keyword": "admin administrative office staff",
        "description": "Administrative staff mengelola dokumen data entry filing scheduling customer service Microsoft Excel surat menyurat dan operasional kantor.",
    },
    {
        "title": "Finance Accounting Staff",
        "company": "Demo",
        "location": "Jakarta",
        "keyword": "finance accounting tax account",
        "description": "Finance accounting staff membuat laporan keuangan invoice account payable account receivable rekonsiliasi bank pajak dan Microsoft Excel.",
    },
    {
        "title": "Graphic Designer",
        "company": "Demo",
        "location": "Remote",
        "keyword": "graphic designer creative visual",
        "description": "Graphic designer membuat social media design branding layout Adobe Photoshop Illustrator Figma typography dan visual campaign.",
    },
    {
        "title": "Production Operator",
        "company": "Demo",
        "location": "Cikarang",
        "keyword": "operator production quality manufacturing",
        "description": "Production operator menjalankan mesin produksi quality control K3 packing laporan shift manufacturing dan target output harian.",
    },
    {
        "title": "HR Recruiter",
        "company": "Demo",
        "location": "Jakarta",
        "keyword": "hr recruiter human resource talent",
        "description": "HR recruiter melakukan recruitment screening CV interview onboarding employee database job posting communication dan hiring coordination.",
    },
    {
        "title": "Sales Marketing Executive",
        "company": "Demo",
        "location": "Surabaya",
        "keyword": "sales marketing business development account executive",
        "description": "Sales marketing executive mencari prospect cold calling customer relationship negotiation sales target presentation CRM dan laporan penjualan.",
    },
]


def fake_extract_text_from_pdf(path):
    return path


def contains_any(text, keywords):
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def run_case(case):
    result = api.analyze_cv_file(case["cvText"], case["targetRole"], case["analysisMode"])
    top_job = result["jobs"][0] if result["jobs"] else {}
    top_text = f"{top_job.get('title', '')} {top_job.get('description', '')}"
    detected = {skill.lower() for skill in result.get("detectedSkills", [])}
    expected_skills = {skill.lower() for skill in case.get("expectedSkills", [])}
    skill_hits = detected & expected_skills

    assert result["score"] > 0, f"{case['id']} expected positive score"
    assert result["jobs"], f"{case['id']} expected job recommendations"
    assert contains_any(top_text, case["expectedTopRoleKeywords"]), (
        f"{case['id']} top job not relevant: {top_job.get('title')}"
    )
    assert not contains_any(top_job.get("title", ""), case["forbiddenTopRoleKeywords"]), (
        f"{case['id']} top job hit forbidden keyword: {top_job.get('title')}"
    )
    assert skill_hits, f"{case['id']} expected at least one skill hit from {expected_skills}, got {detected}"

    return {
        "id": case["id"],
        "topJob": top_job.get("title"),
        "score": result["score"],
        "skillHits": sorted(skill_hits),
    }


def test_recommendation_evaluation():
    original_load_jobs_once = jobs_service.load_jobs_once
    original_extract_text = analysis_service.extract_text_from_pdf
    original_max_candidates = analysis_service.MAX_CANDIDATE_JOBS

    try:
        jobs_service.load_jobs_once = lambda: EVAL_JOBS
        analysis_service.extract_text_from_pdf = fake_extract_text_from_pdf
        jobs_service.PROCESSED_JOBS_CACHE = None
        analysis_service.MAX_CANDIDATE_JOBS = len(EVAL_JOBS)

        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        results = [run_case(case) for case in cases]
        print("EVALUATION PASSED")
        for item in results:
            print(f"OK {item['id']} -> {item['topJob']} ({item['score']}%)")
    finally:
        jobs_service.load_jobs_once = original_load_jobs_once
        analysis_service.extract_text_from_pdf = original_extract_text
        analysis_service.MAX_CANDIDATE_JOBS = original_max_candidates
        jobs_service.PROCESSED_JOBS_CACHE = None


if __name__ == "__main__":
    test_recommendation_evaluation()
