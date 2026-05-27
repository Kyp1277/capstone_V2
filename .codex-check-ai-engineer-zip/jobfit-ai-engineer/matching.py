# =========================================
# SKILL MATCHING MODULE
# =========================================

def match_skills(cv_skills, job_skills):

    # =====================================
    # VALIDASI INPUT
    # =====================================
    if not cv_skills or not job_skills:
        return 0.0

    # =====================================
    # NORMALIZATION
    # =====================================
    cv_set = set([
        skill.strip().lower()
        for skill in cv_skills
    ])

    job_set = set([
        skill.strip().lower()
        for skill in job_skills
    ])

    # =====================================
    # MATCHED SKILLS
    # =====================================
    matched_skills = cv_set & job_set

    # =====================================
    # SCORE COMPONENT
    # =====================================

    # Seberapa banyak kebutuhan job terpenuhi
    required_coverage = len(matched_skills) / len(job_set)

    # Seberapa relevan skill CV terhadap job
    cv_relevance = len(matched_skills) / len(cv_set)

    # =====================================
    # FINAL SCORE
    # =====================================
    final_score = (
        (0.75 * required_coverage) +
        (0.25 * cv_relevance)
    )

    return round(final_score, 3)


# =========================================
# MATCH DETAIL
# =========================================

def get_matching_details(cv_skills, job_skills):

    cv_set = set([
        skill.strip().lower()
        for skill in cv_skills
    ])

    job_set = set([
        skill.strip().lower()
        for skill in job_skills
    ])

    matched = sorted(list(cv_set & job_set))
    missing = sorted(list(job_set - cv_set))

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "total_matched": len(matched),
        "total_missing": len(missing)
    }


# =========================================
# TEST MODULE
# =========================================

if __name__ == "__main__":

    cv = [
        "python",
        "sql",
        "machine learning",
        "docker"
    ]

    job = [
        "python",
        "machine learning",
        "deep learning",
        "sql",
        "rest api"
    ]

    # =====================================
    # SCORE
    # =====================================
    score = match_skills(cv, job)

    # =====================================
    # DETAIL
    # =====================================
    detail = get_matching_details(cv, job)

    print("\nSKILL MATCH ANALYSIS")
    print("=" * 60)

    print(f"\nMatch Score : {round(score * 100, 2)}%")

    print("\nMatched Skills:")
    for skill in detail["matched_skills"]:
        print(f"    {skill}")

    print("\nMissing Skills:")
    for skill in detail["missing_skills"]:
        print(f"    {skill}")

    print("\nSkill Matching Completed Successfully!")