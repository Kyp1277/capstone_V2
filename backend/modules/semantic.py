import logging
import math
import re
from functools import lru_cache


logger = logging.getLogger(__name__)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def clean_text(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", str(text).lower()).strip()


def _token_counts(text):
    counts = {}
    for token in re.findall(r"\b\w{3,}\b", clean_text(text)):
        counts[token] = counts.get(token, 0) + 1
    return counts


def _token_cosine_similarity(text1, text2):
    left = _token_counts(text1)
    right = _token_counts(text2)

    if not left or not right:
        return 0.0

    shared = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))

    if not left_norm or not right_norm:
        return 0.0

    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


@lru_cache(maxsize=1)
def get_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        logger.info("sentence-transformers is unavailable; semantic module uses token fallback.")
        return None

    try:
        return SentenceTransformer(MODEL_NAME)
    except Exception:
        logger.exception("Failed to load semantic model; semantic module uses token fallback.")
        return None


def semantic_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0

    model = get_model()
    if model is None:
        return round(_token_cosine_similarity(text1, text2), 3)

    try:
        embeddings = model.encode([clean_text(text1), clean_text(text2)], convert_to_numpy=True)
        left_vec = embeddings[0]
        right_vec = embeddings[1]
        dot = float((left_vec * right_vec).sum())
        left_norm = math.sqrt(float((left_vec * left_vec).sum()))
        right_norm = math.sqrt(float((right_vec * right_vec).sum()))

        if not left_norm or not right_norm:
            return 0.0

        return round(max(0.0, min(1.0, dot / (left_norm * right_norm))), 3)
    except Exception:
        logger.exception("Semantic similarity failed; using token fallback.")
        return round(_token_cosine_similarity(text1, text2), 3)


def compare_cv_to_job(cv_text, job_description):
    score = semantic_similarity(cv_text, job_description)
    return {
        "semantic_score": score,
        "percentage": round(score * 100, 2),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_cv = "Python developer with Machine Learning, SQL, TensorFlow, NLP, and Docker skills."
    sample_job = "AI Engineer role requiring Python, TensorFlow, NLP, Machine Learning, and SQL."
    print(compare_cv_to_job(sample_cv, sample_job))
