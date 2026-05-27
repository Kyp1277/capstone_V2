import asyncio
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import api
from fastapi import HTTPException


SAMPLE_CV = """
JOHN DOE
PENGALAMAN KERJA
Senior Backend Developer - PT Teknologi Indonesia (2020 - 2024)
Mid Level Backend Developer - PT Digital Solutions (2018 - 2020)
Junior Developer - Startup Tech (2017 - 2018)

PENDIDIKAN
S1 Teknik Informatika - Universitas Indonesia

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, SQL, Git, React
"""


def _processed_job(title, description, skills, keyword="engineer"):
    return {
        "title": title,
        "company": "PT Demo Teknologi",
        "location": "Jakarta",
        "keyword": keyword,
        "description": description,
        "jobText": f"{title}. {description}",
        "jobSkills": skills,
        "jobSkillSet": set(skills),
        "jobDomains": api.infer_job_domains(f"{title}. {keyword}. {description}"),
        "searchText": api.clean_text(f"{title}. {description}"),
        "titleTokens": api.token_set(title),
        "keywordTokens": api.token_set(keyword),
        "descriptionTokens": api.token_set(description),
    }


def _sample_jobs():
    return [
        _processed_job(
            "Senior Backend Engineer",
            "Python FastAPI PostgreSQL Docker Kubernetes SQL Git backend service.",
            ["python", "fastapi", "postgresql", "docker", "kubernetes", "sql", "git"],
        ),
        _processed_job(
            "Sales Representative",
            "Sales customer service communication negotiation retail.",
            ["sales", "customer service", "communication", "negotiation"],
            "sales",
        ),
    ]


class FakeUpload:
    def __init__(self, filename="cv.pdf", content=b"%PDF demo"):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


class MonkeyPatch:
    def __init__(self):
        self._items = []

    def set(self, obj, name, value):
        self._items.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def restore(self):
        for obj, name, value in reversed(self._items):
            setattr(obj, name, value)


def assert_fields(payload):
    required = {
        "id",
        "targetRole",
        "analysisMode",
        "date",
        "score",
        "verdict",
        "summary",
        "detectedSkills",
        "workExperiences",
        "totalExperienceYears",
        "experienceLevel",
        "experienceMatch",
        "missingSkills",
        "improvements",
        "jobs",
        "warnings",
    }
    missing = sorted(required - set(payload))
    assert not missing, f"Missing response fields: {missing}"


def test_valid_cv_contract():
    patch = MonkeyPatch()
    try:
        patch.set(api, "extract_text_from_pdf", lambda _path: SAMPLE_CV)
        patch.set(api, "prepare_jobs_once", _sample_jobs)
        patch.set(api, "semantic_similarity", lambda _left, _right: 0.75)

        payload = api.analyze_cv_file("dummy.pdf", "Senior Backend Engineer", "targeted")
        assert_fields(payload)
        assert payload["analysisMode"] == "targeted"
        assert payload["score"] > 0
        assert payload["workExperiences"], "Expected work experience extraction"
        assert payload["totalExperienceYears"] > 0
        assert payload["experienceLevel"] in {"mid_level", "senior", "senior_manager"}
        assert payload["jobs"], "Expected recommended jobs"

        first_job = payload["jobs"][0]
        for field in ["matchedSkills", "missingSkills", "notFitReason", "improvements", "scoreBreakdown"]:
            assert field in first_job, f"Missing job field: {field}"
    finally:
        patch.restore()


def test_empty_pdf_contract():
    patch = MonkeyPatch()
    try:
        patch.set(api, "extract_text_from_pdf", lambda _path: "")
        patch.set(api, "prepare_jobs_once", _sample_jobs)

        payload = api.analyze_cv_file("empty.pdf", "Backend Engineer", "targeted")
        assert_fields(payload)
        assert payload["score"] == 0
        assert payload["jobs"] == []
        assert payload["workExperiences"] == []
        assert payload["totalExperienceYears"] == 0
        assert payload["experienceLevel"] == "entry_level"
        assert payload["experienceMatch"] == 0
        assert payload["warnings"], "Expected warning for unreadable PDF"
    finally:
        patch.restore()


def test_targeted_requires_target_role():
    try:
        asyncio.run(api.create_analysis(FakeUpload(), "", "targeted"))
    except HTTPException as error:
        assert error.status_code == 400
        assert "Target pekerjaan" in str(error.detail)
    else:
        raise AssertionError("Expected HTTPException for missing targetRole")


def test_auto_mode_allows_empty_target_role():
    patch = MonkeyPatch()
    try:
        captured = {}

        def fake_analyze(path, target_role, mode):
            captured["target_role"] = target_role
            captured["mode"] = mode
            return {
                "id": "analysis-test",
                "targetRole": "Pekerjaan paling cocok dari CV",
                "analysisMode": mode,
                "date": "23 Mei 2026",
                "score": 0,
                "verdict": "Kecocokan Sangat Rendah",
                "summary": "ok",
                "detectedSkills": [],
                "workExperiences": [],
                "totalExperienceYears": 0,
                "experienceLevel": "entry_level",
                "experienceMatch": 0,
                "missingSkills": [],
                "improvements": [],
                "jobs": [],
                "warnings": [],
            }

        patch.set(api, "analyze_cv_file", fake_analyze)
        payload = asyncio.run(api.create_analysis(FakeUpload(), "", "auto"))

        assert payload["analysisMode"] == "auto"
        assert captured == {"target_role": "", "mode": "auto"}
    finally:
        patch.restore()


def run_all():
    tests = [
        test_valid_cv_contract,
        test_empty_pdf_contract,
        test_targeted_requires_target_role,
        test_auto_mode_allows_empty_target_role,
    ]

    for test in tests:
        test()
        print(f"OK {test.__name__}")

    print("ALL API CONTRACT TESTS PASSED")


if __name__ == "__main__":
    run_all()
