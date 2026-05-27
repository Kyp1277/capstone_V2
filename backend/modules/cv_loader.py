import pandas as pd


def load_cv_data(path):

    df = pd.read_csv(path)

    cv_data = []

    for _, row in df.iterrows():

        skills = str(row.get("Extracted_Skills", ""))

        # ubah string jadi list
        skill_list = [
            skill.strip().lower()
            for skill in skills.split(",")
            if skill.strip()
        ]

        cv_data.append({

            "category": row.get("Category", "Unknown"),
            "filename": row.get("Filename", "Unknown"),
            "skills": skill_list,
            "skill_count": row.get("Skill_Count", 0)
        })

    return cv_data