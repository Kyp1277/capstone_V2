from matching import match_skills, get_matching_details


# =========================================
# MATCH LEVEL
# =========================================

def get_match_level(score):

    if score >= 0.80:
        return "Excellent Match"

    elif score >= 0.60:
        return "Strong Match"

    elif score >= 0.40:
        return "Moderate Match"

    elif score >= 0.20:
        return "Low Match"

    else:
        return "Very Low Match"


# =========================================
# RECOMMENDATION ENGINE
# =========================================

def recommend_jobs(

    jobs,
    cv_skills,
    cv_text,

    extract_skills,

    semantic_similarity=None,

    top_k=10
):

    results = []

    # =====================================
    # VALIDASI INPUT
    # =====================================
    if not jobs:
        return []

    if not cv_skills:
        return []

    # =====================================
    # PROCESS ALL JOBS
    # =====================================
    for job in jobs:

        try:

            # =================================
            # JOB DATA
            # =================================
            title = str(job.get("title", "Unknown"))
            company = str(job.get("company", "Unknown"))
            location = str(job.get("location", "Unknown"))
            description = str(job.get("description", ""))

            # =================================
            # NLP SKILL EXTRACTION
            # =================================
            job_skills = extract_skills(
                f"{title} {description}"
            )

            # =================================
            # SKILL MATCHING
            # =================================
            keyword_score = match_skills(
                cv_skills,
                job_skills
            )

            # =================================
            # MATCH DETAILS
            # =================================
            details = get_matching_details(
                cv_skills,
                job_skills
            )

            matched_skills = details["matched_skills"]
            missing_skills = details["missing_skills"]

            # =================================
            # SEMANTIC AI SCORE
            # =================================
            semantic_score = 0

            if semantic_similarity:

                semantic_score = semantic_similarity(
                    cv_text,
                    description
                )

            # =================================
            # MISSING SKILL PENALTY
            # =================================
            missing_penalty = min(
                len(missing_skills) * 0.02,
                0.25
            )

            # =================================
            # FINAL HYBRID SCORE
            # =================================
            final_score = (
                (0.70 * keyword_score)
                +
                (0.30 * semantic_score)
                -
                missing_penalty
            )

            # limit 0 - 1
            final_score = max(
                0,
                min(final_score, 1)
            )

            # =================================
            # NATURAL REASONING
            # =================================
            if final_score >= 0.75:

                reason = (
                    f"Cocok karena memiliki skill "
                    f"{', '.join(matched_skills[:5])} "
                    f"yang sesuai dengan kebutuhan pekerjaan."
                )

            elif final_score >= 0.45:

                reason = (
                    f"Sebagian skill sudah sesuai seperti "
                    f"{', '.join(matched_skills[:5])}, "
                    f"tetapi masih perlu meningkatkan "
                    f"{', '.join(missing_skills[:5])}."
                )

            else:

                reason = (
                    f"Kurang cocok karena skill penting seperti "
                    f"{', '.join(missing_skills[:5])} "
                    f"belum ditemukan pada CV."
                )

            # =================================
            # SAVE RESULT
            # =================================
            results.append({

                "title": title,
                "company": company,
                "location": location,

                "job_skills": job_skills,

                "matched_skills": matched_skills,
                "missing_skills": missing_skills,

                "keyword_score": round(keyword_score, 3),
                "semantic_score": round(semantic_score, 3),

                "final_score": round(final_score, 3),

                "match_level": get_match_level(
                    final_score
                ),

                "reason": reason
            })

        except Exception as e:

            print(
                f"Error processing job "
                f"{job.get('title', 'Unknown')}: {e}"
            )

    # =====================================
    # SORTING BY SCORE
    # =====================================
    results.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    # =====================================
    # RETURN TOP RESULT
    # =====================================
    return results[:top_k]


# =========================================
# TEST MODULE
# =========================================

if __name__ == "__main__":

    from nlp import extract_skills

    # =====================================
    # SAMPLE CV
    # =====================================
    cv_text = """
    Python developer with Machine Learning,
    SQL, Docker, REST API,
    and Data Analysis experience.
    """

    cv_skills = extract_skills(cv_text)

    # =====================================
    # SAMPLE JOBS
    # =====================================
    jobs = [

        {
            "title": "AI Engineer",
            "company": "OpenAI",
            "location": "Remote",

            "description": """
            Looking for AI Engineer with Python,
            Machine Learning, Docker,
            REST API, and SQL experience.
            """
        },

        {
            "title": "Frontend Developer",
            "company": "Google",
            "location": "Remote",

            "description": """
            Need React Developer with CSS,
            JavaScript, Figma,
            and UI UX skills.
            """
        }
    ]

    # =====================================
    # RECOMMENDATION
    # =====================================
    recommendations = recommend_jobs(

        jobs=jobs,

        cv_skills=cv_skills,
        cv_text=cv_text,

        extract_skills=extract_skills,

        semantic_similarity=None,

        top_k=5
    )

    # =====================================
    # OUTPUT
    # =====================================
    print("\nJOB RECOMMENDATION RESULT")
    print("=" * 70)

    for i, job in enumerate(recommendations, 1):

        print(f"\nTOP #{i}")
        print("-" * 70)

        print(f"Job Title   : {job['title']}")
        print(f"Company     : {job['company']}")

        print(
            f"Final Score : "
            f"{round(job['final_score'] * 100, 2)}%"
        )

        print(f"Match Level : {job['match_level']}")

        print("\nMatched Skills:")
        for skill in job["matched_skills"]:
            print(f"    {skill}")

        print("\nMissing Skills:")
        for skill in job["missing_skills"]:
            print(f"    {skill}")

        print(f"\nReason:")
        print(f"   {job['reason']}")