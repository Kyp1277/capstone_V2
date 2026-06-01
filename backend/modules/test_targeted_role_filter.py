from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api  # noqa: E402
from modules import analysis_service, jobs_service  # noqa: E402


JOBS = [
    {
        "title": "Telemarketing",
        "company": "Demo",
        "location": "Jakarta",
        "keyword": "telemarketing sales customer database",
        "description": "Telemarketing menghubungi pelanggan, memakai database customer, komunikasi, teamwork, dan target penjualan.",
    },
    {
        "title": "Koki Cafe",
        "company": "Demo",
        "location": "Bandung",
        "keyword": "koki cafe kitchen cook dapur",
        "description": "Koki cafe menyiapkan masakan, bekerja di dapur, memasak sesuai menu, menjaga kebersihan kitchen, dan mengikuti SOP restoran.",
    },
    {
        "title": "Cook - Kitchen Staff",
        "company": "Demo",
        "location": "Jakarta",
        "keyword": "cook kitchen staff chef culinary",
        "description": "Cook kitchen staff menyiapkan bahan makanan, memasak, menjaga hygiene dapur, dan bekerja sama dengan service team.",
    },
]


def fake_extract_text_from_pdf(path):
    return path


def test_targeted_koki_prefers_culinary_jobs():
    original_load_jobs_once = jobs_service.load_jobs_once
    original_extract_text = analysis_service.extract_text_from_pdf

    try:
        jobs_service.load_jobs_once = lambda: JOBS
        analysis_service.extract_text_from_pdf = fake_extract_text_from_pdf
        jobs_service.PROCESSED_JOBS_CACHE = None

        result = api.analyze_cv_file(
            "Mahasiswa Sistem Informasi. Skill database, communication, teamwork, leadership, problem solving. Pernah membantu acara memasak kampus.",
            "koki",
            "targeted",
        )

        assert result["jobs"], "Expected job recommendations"
        top_title = result["jobs"][0]["title"].lower()
        assert "koki" in top_title or "cook" in top_title or "kitchen" in top_title, top_title
        assert "telemarketing" not in top_title, top_title
    finally:
        jobs_service.load_jobs_once = original_load_jobs_once
        analysis_service.extract_text_from_pdf = original_extract_text
        jobs_service.PROCESSED_JOBS_CACHE = None


def test_targeted_koki_without_culinary_evidence_stays_low():
    original_load_jobs_once = jobs_service.load_jobs_once
    original_extract_text = analysis_service.extract_text_from_pdf

    try:
        jobs_service.load_jobs_once = lambda: JOBS
        analysis_service.extract_text_from_pdf = fake_extract_text_from_pdf
        jobs_service.PROCESSED_JOBS_CACHE = None

        result = api.analyze_cv_file(
            "Mahasiswa Sistem Informasi dan Management. Skill database, JavaScript, React, communication, teamwork, leadership, problem solving.",
            "koki",
            "targeted",
        )

        assert result["score"] < 30, result
        assert all(job["match"] < 40 for job in result["jobs"]), result["jobs"]
    finally:
        jobs_service.load_jobs_once = original_load_jobs_once
        analysis_service.extract_text_from_pdf = original_extract_text
        jobs_service.PROCESSED_JOBS_CACHE = None


if __name__ == "__main__":
    test_targeted_koki_prefers_culinary_jobs()
    test_targeted_koki_without_culinary_evidence_stays_low()
    print("TARGETED ROLE FILTER TESTS PASSED")
