# =========================================
# PREPROCESS JOBS DATASET
# File: preprocess_jobs.py
# =========================================

import pandas as pd
from modules.nlp import extract_skills


# =========================================
# LOAD DATASET
# =========================================
def load_dataset(path="data/jobs_clean.csv"):

    try:
        df = pd.read_csv(path)

        print(f"\n Dataset berhasil dimuat!")
        print(f" Total data: {len(df)}")

        return df

    except FileNotFoundError:
        print(" File dataset tidak ditemukan.")
        return None


# =========================================
# PREPROCESS DATASET
# =========================================
def preprocess_jobs(df):

    processed_jobs = []

    print("\n Memulai NLP Skill Extraction...\n")

    for index, row in df.iterrows():

        # ambil description
        description = str(row.get("description", ""))

        # extract skills
        skills = extract_skills(description)

        # simpan hasil
        processed_jobs.append({
            "job_no": row.get("job_no"),
            "title": row.get("title"),
            "company": row.get("company"),
            "location": row.get("location"),
            "keyword": row.get("keyword"),
            "skills": ", ".join(skills),
            "description": description
        })

        # progress setiap 100 data
        if (index + 1) % 100 == 0:
            print(f" Processed {index + 1} jobs...")

    print("\n NLP preprocessing selesai!")

    return pd.DataFrame(processed_jobs)


# =========================================
# SAVE PROCESSED DATA
# =========================================
def save_processed_data(df, output_path="data/jobs_processed.csv"):

    df.to_csv(output_path, index=False)

    print(f"\n Processed dataset berhasil disimpan:")
    print(f" {output_path}")


# =========================================
# MAIN PROGRAM
# =========================================
def main():

    # 1. Load dataset scraping
    df = load_dataset()

    if df is None:
        return

    # 2. NLP preprocessing
    processed_df = preprocess_jobs(df)

    # 3. Simpan hasil
    save_processed_data(processed_df)

    # 4. Preview hasil
    print("\n Sample Processed Data:\n")

    print(processed_df.head())


# =========================================
# ENTRY POINT
# =========================================
if __name__ == "__main__":
    main()