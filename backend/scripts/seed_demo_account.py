from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules import database  # noqa: E402


DEMO_EMAIL = "demo@jobfit.local"
DEMO_PASSWORD = "demo1234"


def main():
    database.ensure_database_schema()
    user = database.create_or_update_unverified_user("Demo JobFit", DEMO_EMAIL, DEMO_PASSWORD)
    if user:
        with database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET email_verified = TRUE, updated_at = NOW()
                    WHERE email = %s
                    """,
                    (DEMO_EMAIL,),
                )
            connection.commit()
        user = database.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD)
    else:
        user = database.authenticate_user(DEMO_EMAIL, DEMO_PASSWORD)

    if not user:
        raise RuntimeError("Akun demo gagal dibuat.")

    demo_result = {
        "id": "demo-analysis-ai-engineer",
        "targetRole": "AI Engineer",
        "analysisMode": "targeted",
        "date": "25 Mei 2026",
        "score": 84,
        "verdict": "Kecocokan Tinggi",
        "summary": "CV demo kuat untuk AI Engineer karena menonjolkan Python, API, NLP, database, dan deployment. Gap utama adalah evaluasi model dan monitoring.",
        "detectedSkills": ["python", "fastapi", "nlp", "postgresql", "docker", "git"],
        "missingSkills": ["model evaluation", "ml monitoring", "prompt evaluation"],
        "improvements": [
            "Tambahkan bukti evaluasi model dengan metrik yang jelas.",
            "Perjelas pengalaman deploy API AI ke environment production-like.",
            "Tambahkan contoh monitoring kualitas rekomendasi."
        ],
        "workExperiences": [
            {
                "position": "Backend AI Developer",
                "company": "Capstone Project",
                "duration": "2025 - 2026",
                "level": "junior"
            }
        ],
        "totalExperienceYears": 1,
        "experienceLevel": "junior",
        "experienceMatch": 76,
        "jobs": [
            {
                "title": "AI Engineer",
                "match": 84,
                "matchedSkills": ["python", "fastapi", "nlp", "postgresql"],
                "missingSkills": ["model evaluation", "ml monitoring"],
                "detail": "Cocok karena CV menunjukkan Python, NLP, API, dan database yang relevan untuk role AI Engineer.",
                "notFitReason": "Perlu memperjelas evaluasi kualitas model dan monitoring hasil rekomendasi.",
                "improvements": ["Tambahkan metrik evaluasi model.", "Jelaskan proses monitoring rekomendasi."],
                "scoreBreakdown": {
                    "skillMatch": 86,
                    "semanticMatch": 82,
                    "roleMatch": 88,
                    "contextMatch": 78,
                    "educationMatch": 80
                }
            }
        ],
        "warnings": []
    }

    database.save_analysis(user["id"], demo_result, "Demo CV text untuk presentasi JobFit.")
    print("Akun demo siap:")
    print(f"Email: {DEMO_EMAIL}")
    print(f"Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
