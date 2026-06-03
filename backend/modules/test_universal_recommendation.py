import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules import analysis_service, nlp  # noqa: E402


BLOCKED_TEXT = {
    "tensorflow",
    "pytorch",
    "tensorflow hub",
    "automl",
    "chatgpt",
    "gemini",
    "openai",
}


def _joined(items):
    return "\n".join(items).lower()


def test_safe_recommendation_database_has_no_forbidden_content():
    assert nlp.SAFE_RECOMMENDATION_DATABASE

    hits = []
    for skill, entry in nlp.SAFE_RECOMMENDATION_DATABASE.items():
        text = f"{skill} {entry.get('course', '')} {entry.get('project', '')}".lower()
        hits.extend((skill, token) for token in BLOCKED_TEXT if token in text)

    assert hits == []


def test_backend_recommendations_ignore_off_role_courses():
    tips = analysis_service.build_improvements(
        detected_skills=["python", "mysql"],
        missing_skills=["accounting", "agile", "api", "aws", "docker", "fastapi"],
        weighted_skills={"python": 1.8, "mysql": 1.6},
        target_role="Backend Developer",
        target_family="backend",
    )
    text = _joined(tips)

    assert "docker" in text
    assert "fastapi" in text
    assert "accounting" not in text
    assert "aws" not in text
    assert "agile" not in text


def test_data_ml_recommendations_stay_local_and_rule_based():
    tips = analysis_service.build_improvements(
        detected_skills=["python", "mysql"],
        missing_skills=["sql", "machine learning", "postgresql"],
        weighted_skills={"python": 1.8, "mysql": 1.6},
        target_role="Machine Learning Engineer",
        target_family="data",
    )
    text = _joined(tips)

    assert "sql" in text
    assert "machine learning" in text
    assert "evaluasi data secara lokal" in text
    assert not any(token in text for token in BLOCKED_TEXT)


def test_roadmap_projects_follow_role_family():
    backend_steps, backend_projects = analysis_service.build_career_roadmap(
        "backend",
        ["git", "laravel", "mongodb", "accounting"],
        ["python", "mysql"],
        "entry_level",
    )
    backend_steps_text = _joined(backend_steps)
    backend_text = _joined(backend_projects)

    assert "git" in backend_steps_text
    assert "laravel" in backend_steps_text
    assert "mongodb" in backend_steps_text
    assert "github" in backend_text
    assert "autentikasi" in backend_text
    assert "database non-relasional" in backend_text
    assert "laporan neraca" not in backend_text


def run_all():
    tests = [
        test_safe_recommendation_database_has_no_forbidden_content,
        test_backend_recommendations_ignore_off_role_courses,
        test_data_ml_recommendations_stay_local_and_rule_based,
        test_roadmap_projects_follow_role_family,
    ]

    for test in tests:
        test()
        print(f"OK {test.__name__}")

    print("UNIVERSAL RECOMMENDATION TESTS PASSED")


if __name__ == "__main__":
    run_all()
