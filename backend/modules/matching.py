def match_skills(cv_skills, job_skills):
    match_count = len(set(cv_skills) & set(job_skills))
    total = len(set(job_skills))

    if total == 0:
        return 0

    score = match_count / total
    return round(score, 2)


# TEST
if __name__ == "__main__":
    cv = ["python", "sql", "machine learning"]
    job = ["python", "machine learning", "deep learning"]

    score = match_skills(cv, job)
    print("Match Score:", score)