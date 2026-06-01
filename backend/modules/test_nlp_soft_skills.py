from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.nlp import extract_skills, extract_technical_skills, extract_weighted_skills, infer_job_domains


def test_extract_skills_keeps_soft_skills_by_default():
    skills = extract_skills("Python teamwork leadership")

    assert "python" in skills
    assert "teamwork" in skills
    assert "leadership" in skills


def test_extract_skills_can_exclude_soft_skills():
    skills = extract_skills("Python teamwork leadership", include_soft_skills=False)

    assert skills == ["python"]
    assert extract_technical_skills("Python teamwork leadership") == ["python"]


def test_weighted_skills_downweight_soft_skills():
    weights = extract_weighted_skills("Python Python teamwork teamwork")

    assert weights["python"] > weights["teamwork"]
    assert weights["teamwork"] < 1.0


def test_expanded_skill_database_detects_modern_frontend_and_logistics():
    frontend_skills = set(extract_skills("Next.js Tailwind CSS GraphQL Redis AWS Scrum"))
    logistics_skills = set(
        extract_skills("Mengelola supply chain warehouse inventory logistics procurement")
    )
    domains = set(infer_job_domains("Warehouse logistics supply chain inventory procurement"))

    assert {"next.js", "tailwind css", "graphql", "redis", "aws"} <= frontend_skills
    assert {"supply chain", "warehouse", "inventory", "procurement"} <= logistics_skills
    assert "logistics" in domains


if __name__ == "__main__":
    test_extract_skills_keeps_soft_skills_by_default()
    test_extract_skills_can_exclude_soft_skills()
    test_weighted_skills_downweight_soft_skills()
    test_expanded_skill_database_detects_modern_frontend_and_logistics()
    print("NLP SOFT SKILL TESTS PASSED")
