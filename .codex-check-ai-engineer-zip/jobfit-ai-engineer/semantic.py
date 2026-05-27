from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# =========================================
# LOAD SEMANTIC AI MODEL
# =========================================

print(" Loading Semantic AI Model...")

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

print(" Semantic Model Loaded Successfully!")


# =========================================
# TEXT CLEANING
# =========================================
def clean_text(text):
    """
    Membersihkan text sebelum embedding
    """

    if not text:
        return ""

    text = str(text).lower().strip()

    return text


# =========================================
# TEXT EMBEDDING
# =========================================
def get_embedding(text):
    """
    Mengubah text menjadi vector embedding
    menggunakan Sentence-BERT
    """

    # validasi input
    if not text or not isinstance(text, str):

        # ukuran vector MiniLM-L6-v2 = 384
        return np.zeros(384)

    # cleaning
    text = clean_text(text)

    # encoding text
    embedding = model.encode(
        text,
        convert_to_numpy=True
    )

    return embedding


# =========================================
# SEMANTIC SIMILARITY
# =========================================
def semantic_similarity(text1, text2):
    """
    Menghitung semantic similarity
    antara CV dan Job Description
    """

    # validasi input
    if not text1 or not text2:
        return 0.0

    # embedding
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)

    # cosine similarity
    similarity_score = cosine_similarity(
        [emb1],
        [emb2]
    )[0][0]

    # normalisasi
    similarity_score = float(similarity_score)

    # hindari minus
    similarity_score = max(0.0, similarity_score)

    return round(similarity_score, 3)


# =========================================
# CV VS JOB MATCHING
# =========================================
def compare_cv_to_job(cv_text, job_description):
    """
    Membandingkan isi CV dengan job description
    """

    score = semantic_similarity(
        cv_text,
        job_description
    )

    return {
        "semantic_score": score,
        "percentage": round(score * 100, 2)
    }


# =========================================
# TEST MODULE
# =========================================
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print(" SEMANTIC AI TEST")
    print("=" * 60)

    # =====================================
    # SAMPLE CV
    # =====================================
    cv_text = """
    Python developer with Machine Learning,
    SQL, Deep Learning, TensorFlow,
    Data Analysis, NLP, and Docker skills.
    """

    # =====================================
    # SAMPLE JOB
    # =====================================
    job_description = """
    We are looking for AI Engineer with
    Python, TensorFlow, NLP,
    Machine Learning, and SQL experience.
    """

    # =====================================
    # SEMANTIC MATCHING
    # =====================================
    result = compare_cv_to_job(
        cv_text,
        job_description
    )

    print("\n CV Content:")
    print(cv_text)

    print("\n Job Description:")
    print(job_description)

    print("\n Semantic Matching Result")
    print("-" * 60)

    print(f" Semantic Score : {result['semantic_score']}")
    print(f" Match Percent  : {result['percentage']}%")

    # =====================================
    # MATCH LEVEL
    # =====================================
    if result['semantic_score'] >= 0.80:
        print(" Excellent Match")

    elif result['semantic_score'] >= 0.60:
        print(" Strong Match")

    elif result['semantic_score'] >= 0.40:
        print(" Moderate Match")

    else:
        print(" Low Match")

    print("=" * 60)