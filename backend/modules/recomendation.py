# =========================================
# RECOMMENDATION ENGINE
# =========================================

def recommend_jobs(
    jobs,
    extract_skills,
    semantic_similarity=None,
    top_k=10,
    alpha=0.7
):

    results = []

    # =====================================
    # REFERENCE QUERY
    # =====================================
    # acuan pekerjaan terbaik
    reference_query = """
    Looking for candidates with skills in
    technology, communication, leadership,
    data analysis, problem solving,
    programming, management, and teamwork.
    """

    for job in jobs:

        try:
            # =================================
            # JOB DATA
            # =================================
            title = job.get("title", "Unknown")
            company = job.get("company", "Unknown")
            location = job.get("location", "Unknown")
            description = job.get("description", "")

            # =================================
            # NLP SKILL EXTRACTION
            # =================================
            job_skills = extract_skills(description)

            # =================================
            # SKILL SCORE
            # =================================
            # semakin banyak skill semakin tinggi
            skill_score = min(len(job_skills) / 10, 1.0)

            # =================================
            # SEMANTIC SCORE
            # =================================
            semantic_score = 0

            if semantic_similarity:
                semantic_score = semantic_similarity(
                    reference_query,
                    description
                )

            # =================================
            # FINAL HYBRID SCORE
            # =================================
            final_score = (
                (alpha * semantic_score)
                +
                ((1 - alpha) * skill_score)
            )

            # =================================
            # SAVE RESULT
            # =================================
            results.append({

                "title": title,
                "company": company,
                "location": location,

                "job_skills": job_skills,

                "semantic_score": round(semantic_score, 3),
                "skill_score": round(skill_score, 3),

                "score": round(final_score, 3)
            })

        except Exception as e:
            print(f"Error processing job: {e}")

    # =====================================
    # SORTING RANKING
    # =====================================
    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # =====================================
    # RETURN TOP RESULT
    # =====================================
    return results[:top_k]