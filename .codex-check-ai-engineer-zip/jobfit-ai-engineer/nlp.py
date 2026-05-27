import re

# =========================================
# MASTER SKILL DATABASE
# =========================================

SKILL_LIST = [

    # =====================================
    # SOFTWARE, DATA & AI
    # =====================================
    "python",
    "java",
    "javascript",
    "typescript",
    "php",
    "c++",
    "c#",
    "html",
    "css",
    "react",
    "vue",
    "angular",
    "node.js",
    "express",
    "laravel",
    "django",
    "flask",
    "fastapi",
    "rest api",
    "git",
    "github",
    "docker",
    "kubernetes",
    "linux",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "firebase",
    "database",
    "database management",
    "data analysis",
    "data analyst",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "nlp",
    "natural language processing",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "pandas",
    "numpy",
    "power bi",
    "tableau",
    "excel",
    "microsoft excel",
    "figma",
    "ui ux",

    # =====================================
    # BUSINESS, FINANCE & ADMIN
    # =====================================
    "accounting",
    "finance",
    "tax",
    "pajak",
    "accurate",
    "erp",
    "administrative",
    "administration",
    "microsoft office",
    "word",
    "powerpoint",
    "customer service",
    "sales",
    "marketing",
    "digital marketing",
    "copywriting",
    "recruitment",
    "human resources",
    "payroll",

    # =====================================
    # SOFT SKILLS
    # =====================================
    "problem solving",
    "time management",
    "effective communication",
    "teamwork",
    "collaboration",
    "leadership",

    # =====================================
    # ENGINEERING & CONSTRUCTION
    # =====================================
    "civil engineering",
    "mechanical engineering",
    "electrical engineering",
    "industrial engineering",
    "project management",
    "site engineer",
    "site supervisor",
    "drafter",
    "autocad",
    "civil 3d",
    "quantity surveyor",
    "estimator",
    "engineering drawing",
    "technical drawing",

    # =====================================
    # HOSPITALITY & HOTEL
    # =====================================
    "housekeeping",
    "hotel management",
    "front office",
    "receptionist",
    "guest service",
    "room attendant",
    "hospitality",

    # =====================================
    # MANUFACTURING & TECHNICAL
    # =====================================
    "maintenance",
    "mechanic",
    "welding",
    "cnc",
    "fabrication",
    "technician",
    "production operator",
    "machine operator"
]


# =========================================
# SYNONYM NORMALIZATION
# =========================================

SKILL_SYNONYMS = {

    # Excel
    "ms excel": "excel",
    "microsoft excel": "excel",

    # Office
    "ms office": "microsoft office",

    # Programming
    "js": "javascript",
    "nodejs": "node.js",

    # AI
    "ai": "artificial intelligence",
    "ml": "machine learning",

    # HR
    "hrd": "human resources",

    # UI UX
    "ui/ux": "ui ux",

    # Database
    "basis data": "database",
    "pengolahan database": "database management",

    # Indonesian normalization
    "pemrograman": "programming",
    "manajemen waktu": "time management",
    "komunikasi efektif": "effective communication",
    "kerja tim": "teamwork",
    "kolaborasi": "collaboration",

    # Customer Service
    "cs": "customer service",

    # Finance
    "finance staff": "finance",

    # Admin
    "admin": "administrative"
}


# =========================================
# STOPWORDS
# =========================================

STOPWORDS = {
    "dan",
    "atau",
    "yang",
    "dengan",
    "untuk",
    "dalam",
    "pada",
    "the",
    "and",
    "for",
    "with",
    "required",
    "preferred",
    "experience",
    "candidate",
    "job",
    "work",
    "position",
    "role",
    "staff",
    "senior",
    "junior"
}


# =========================================
# TEXT CLEANING
# =========================================

def clean_text(text):

    if not isinstance(text, str):
        return ""

    # lowercase
    text = text.lower()

    # remove url
    text = re.sub(r"http\S+|www\S+", " ", text)

    # remove email
    text = re.sub(r"\S+@\S+", " ", text)

    # keep special chars
    text = re.sub(r"[^a-zA-Z0-9\s\+\#\.]", " ", text)

    # remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


# =========================================
# NORMALIZE TEXT
# =========================================

def normalize_text(text):

    text = clean_text(text)

    for short_term, real_skill in SKILL_SYNONYMS.items():

        pattern = r"\b" + re.escape(short_term.lower()) + r"\b"

        text = re.sub(pattern, real_skill, text)

    return text


# =========================================
# NLP SKILL EXTRACTION
# =========================================

def extract_skills(text):

    if not text:
        return []

    cleaned_text = normalize_text(text)

    found_skills = set()

    # =====================================
    # SKILL LIST MATCHING
    # =====================================
    for skill in SKILL_LIST:

        pattern = r"\b" + re.escape(skill.lower()) + r"\b"

        if re.search(pattern, cleaned_text):
            found_skills.add(skill)

    # =====================================
    # REMOVE DUPLICATES
    # =====================================
    cleaned_skills = []

    for skill in sorted(found_skills):

        # skip meaningless word
        if skill in STOPWORDS:
            continue

        # skip too short
        if len(skill.strip()) < 2:
            continue

        cleaned_skills.append(skill)

    return cleaned_skills


# =========================================
# JOB ANALYSIS
# =========================================

def analyze_job_description(job):

    title = job.get("title", "Unknown")
    description = job.get("description", "")

    skills = extract_skills(description)

    return {
        "title": title,
        "total_skills": len(skills),
        "skills": skills
    }


# =========================================
# TEST MODULE
# =========================================

if __name__ == "__main__":

    sample_job = {
        "title": "AI Engineer",
        "description": """
        We are looking for AI Engineer with Python,
        Machine Learning, TensorFlow, SQL,
        Docker, REST API, and Data Analysis experience.
        Must understand Microsoft Excel and teamwork.
        """
    }

    result = analyze_job_description(sample_job)

    print("\nNLP JOB ANALYSIS")
    print("=" * 60)

    print(f"\nJob Title : {result['title']}")
    print(f"Total Skills : {result['total_skills']}")

    print("\nExtracted Skills:\n")

    for skill in result["skills"]:
        print(f"    {skill}")

    print("\nNLP Extraction Completed Successfully!")