import re
from collections import Counter

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
"api",
"git",
"github",
"docker",
"kubernetes",
"linux",
"sql",
"mysql",
"database",
"database management",
"postgresql",
"mongodb",
"firebase",
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
"hr",
"payroll",
"programming",
"time management",
"problem solving",
"effective communication",
"teamwork",
"collaboration",

# =====================================
# ENGINEERING & CONSTRUCTION
# =====================================
"civil engineering",
"mechanical engineering",
"electrical engineering",
"industrial engineering",
"project manager",
"project management",
"site engineer",
"site supervisor",
"drafter",
"autocad",
"civil 3d",
"drafter civil 3d",
"quantity surveyor",
"estimator",
"engineering drawing",
"technical drawing",

# =====================================
# HOSPITALITY & HOTEL
# =====================================
"housekeeping",
"staff housekeeping",
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
# Membantu NLP membaca variasi kata

SKILL_SYNONYMS = {

    # Excel
    "ms excel": "excel",
    "microsoft excel": "excel",

    # AI
    "ai": "artificial intelligence",
    "ml": "machine learning",

    # HR
    "hrd": "human resources",

    # UI UX
    "ui/ux": "ui ux",

    # Office
    "ms office": "microsoft office",

    # Programming
    "js": "javascript",
    "pemrograman": "programming",
    "pengolahan database": "database management",
    "basis data": "database",
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


SKILL_CANONICALS = {skill: skill for skill in SKILL_LIST}
SKILL_CANONICALS.update(SKILL_SYNONYMS)

SKILL_PATTERNS = [
    (alias, canonical, re.compile(r"\b" + re.escape(alias.lower()) + r"\b"))
    for alias, canonical in sorted(SKILL_CANONICALS.items(), key=lambda item: len(item[0]), reverse=True)
]
SKILL_LOOKUP = {alias.lower(): canonical for alias, canonical in SKILL_CANONICALS.items()}
SKILL_ALIAS_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9\+\#\.])("
    + "|".join(re.escape(alias.lower()) for alias in sorted(SKILL_CANONICALS, key=len, reverse=True))
    + r")(?![a-zA-Z0-9\+\#\.])"
)

CONTEXT_KEYWORDS = {
    "project",
    "projects",
    "portfolio",
    "experience",
    "experienced",
    "pengalaman",
    "proyek",
    "membangun",
    "mengembangkan",
    "developed",
    "built",
    "implemented",
    "certification",
    "certified",
    "sertifikasi",
    "tools",
    "tool",
    "tech",
    "stack",
}

MAX_SKILL_WEIGHT = 3.0

EDUCATION_DOMAIN_PATTERNS = {
    "it": [
        "teknik informatika",
        "informatika",
        "sistem informasi",
        "ilmu komputer",
        "computer science",
        "information technology",
        "software engineering",
        "rekayasa perangkat lunak",
        "teknologi informasi",
    ],
    "data_ai": [
        "data science",
        "sains data",
        "statistika",
        "matematika",
        "artificial intelligence",
        "machine learning",
    ],
    "finance": [
        "akuntansi",
        "accounting",
        "finance",
        "keuangan",
        "perpajakan",
        "tax",
    ],
    "business": [
        "manajemen",
        "management",
        "administrasi bisnis",
        "business administration",
        "marketing",
        "pemasaran",
    ],
    "design": [
        "desain komunikasi visual",
        "dkv",
        "design",
        "desain grafis",
        "ui ux",
    ],
    "engineering": [
        "teknik sipil",
        "civil engineering",
        "teknik mesin",
        "mechanical engineering",
        "teknik elektro",
        "electrical engineering",
        "teknik industri",
        "industrial engineering",
    ],
    "hospitality": [
        "perhotelan",
        "hospitality",
        "hotel management",
        "pariwisata",
    ],
}

JOB_DOMAIN_KEYWORDS = {
    "it": [
        "frontend",
        "backend",
        "fullstack",
        "developer",
        "software",
        "programmer",
        "web",
        "mobile",
        "qa",
        "quality assurance",
        "devops",
        "network",
        "database",
        "system",
        "it",
    ],
    "data_ai": [
        "data",
        "scientist",
        "analyst",
        "machine learning",
        "ai",
        "artificial intelligence",
        "nlp",
        "business intelligence",
    ],
    "finance": [
        "accounting",
        "accountant",
        "finance",
        "tax",
        "pajak",
        "audit",
        "bookkeeping",
    ],
    "business": [
        "business",
        "marketing",
        "sales",
        "administrative",
        "administration",
        "customer service",
        "hr",
        "human resources",
        "recruitment",
    ],
    "design": [
        "designer",
        "ui ux",
        "figma",
        "creative",
        "graphic",
        "product design",
    ],
    "engineering": [
        "civil",
        "mechanical",
        "electrical",
        "industrial",
        "civil engineer",
        "mechanical engineer",
        "electrical engineer",
        "industrial engineer",
        "site engineer",
        "drafter",
        "autocad",
        "quantity surveyor",
    ],
    "hospitality": [
        "hotel",
        "hospitality",
        "housekeeping",
        "front office",
        "receptionist",
        "guest service",
    ],
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

    # keep special chars for c++, c#, node.js
    text = re.sub(r"[^a-zA-Z0-9\s\+\#\.]", " ", text)

    # remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


# =========================================
# NLP SKILL EXTRACTION
# =========================================
def extract_skills(text):

    if not text:
        return []

    cleaned_text = clean_text(text)

    found_skills = set()

    for match in SKILL_ALIAS_PATTERN.finditer(cleaned_text):
        found_skills.add(SKILL_LOOKUP[match.group(1)])

    # =====================================
    # 3. SORTING
    # =====================================
    found_skills = sorted(list(found_skills))

    return found_skills


def extract_weighted_skills(text):
    if not text:
        return {}

    cleaned_text = clean_text(text)
    skill_counts = Counter()
    context_bonus = Counter()

    for match in SKILL_ALIAS_PATTERN.finditer(cleaned_text):
        canonical_skill = SKILL_LOOKUP[match.group(1)]
        skill_counts[canonical_skill] += 1

        left = max(0, match.start() - 80)
        right = min(len(cleaned_text), match.end() + 80)
        context = cleaned_text[left:right]
        if any(keyword in context for keyword in CONTEXT_KEYWORDS):
            context_bonus[canonical_skill] += 1

    weighted_skills = {}
    for skill, count in skill_counts.items():
        frequency_weight = 1.0 + min(1.2, (count - 1) * 0.35)
        context_weight = min(0.8, context_bonus[skill] * 0.25)
        weighted_skills[skill] = round(min(MAX_SKILL_WEIGHT, frequency_weight + context_weight), 3)

    return dict(sorted(weighted_skills.items(), key=lambda item: (-item[1], item[0])))


def extract_education_profile(text):
    cleaned_text = clean_text(text)
    matched_domains = set()
    matched_majors = set()

    for domain, patterns in EDUCATION_DOMAIN_PATTERNS.items():
        for pattern in patterns:
            if re.search(r"\b" + re.escape(pattern) + r"\b", cleaned_text):
                matched_domains.add(domain)
                matched_majors.add(pattern)

    degree_matches = set(
        re.findall(
            r"\b(sma|smk|d1|d2|d3|d4|s1|s2|s3|sarjana|bachelor|master|magister)\b",
            cleaned_text,
        )
    )

    return {
        "domains": sorted(matched_domains),
        "majors": sorted(matched_majors),
        "degrees": sorted(degree_matches),
    }


def infer_job_domains(text):
    cleaned_text = clean_text(text)
    domains = set()

    for domain, keywords in JOB_DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword) + r"\b", cleaned_text):
                domains.add(domain)
                break

    return sorted(domains)


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
        Docker, and Data Analysis experience.
        Must understand Microsoft Excel and teamwork.
        """
    }

    result = analyze_job_description(sample_job)

    print("\n NLP JOB ANALYSIS")
    print("=" * 60)

    print(f"\n Job Title : {result['title']}")
    print(f" Total Skills : {result['total_skills']}")

    print("\n Extracted Skills:\n")

    for skill in result["skills"]:
        print(f"    {skill}")

    print("\n NLP Extraction Completed Successfully!")
