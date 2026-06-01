import re
from collections import Counter
from datetime import datetime

try:
    from rapidfuzz import fuzz as _rfuzz, process as _rprocess
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False

NLP_CACHE_VERSION = "work-experience-v1.3-skill-db-expanded-domains-2026-05-30"

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
# DEVOPS, CLOUD & MODERN FRONTEND
# =====================================
"next.js",
"nuxt",
"svelte",
"tailwind css",
"graphql",
"prisma",
"redis",
"supabase",
"elasticsearch",
"terraform",
"ansible",
"jenkins",
"ci/cd",
"github actions",
"gitlab ci",
"aws",
"amazon web services",
"google cloud",
"gcp",
"prometheus",
"grafana",
"devops",
"nginx",
"apache",

# =====================================
# PROJECT MANAGEMENT & AGILE
# =====================================
"agile",
"scrum",
"kanban",
"jira",
"confluence",
"trello",
"notion",
"product management",
"sprint planning",

# =====================================
# DATA & ANALYTICS (EXTENDED)
# =====================================
"r",
"matlab",
"spss",
"sas",
"airflow",
"spark",
"hadoop",
"kafka",
"dbt",
"looker",
"metabase",
"google analytics",
"seo",
"sem",

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
"sap",
"oracle",
"audit",
"compliance",
"risk management",
"budgeting",
"forecasting",
"financial analysis",
"procurement",
"supply chain",
"logistics",
"logistik",
"warehouse",
"inventory",
"content writing",
"social media",
"email marketing",
"training",
"performance management",
"time management",
"problem solving",
"effective communication",
"teamwork",
"collaboration",
"leadership",
"communication",
"interpersonal",
"adaptability",
"creativity",
"critical thinking",
"organizational",

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
"machine operator",
"cooking",
"memasak",
"cook",
"chef",
"kitchen",
"dapur",
"culinary",
"tata boga",
"food safety",
"hygiene",
"food preparation",

# =====================================
# IT INFRASTRUCTURE & NETWORKING
# =====================================
"active directory",
"group policy",
"powershell",
"azure",
"microsoft azure",
"office 365",
"microsoft exchange",
"exchange",
"vmware",
"vsphere",
"virtualization",
"virtual machine",
"vdi",
"veeam",
"backup",
"disaster recovery",
"dns",
"dhcp",
"tcp/ip",
"vpn",
"firewall",
"network security",
"networking",
"lan",
"wan",
"wireless",
"sccm",
"windows server",
"active sync",
"ldap",
"iis",
"sharepoint",
"solarwinds",
"troubleshooting",
"server management",
"storage management",
"cloud computing",
"iaas",
"saas",
"bash",
"vbscript",
"batch scripting",
"mcafee",
"antivirus",
"patch management",
"system administration",
"help desk",
"technical support",
"it support",
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
    "coding": "programming",
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
    "admin": "administrative",

    # IT Infrastructure
    "ad": "active directory",
    "gpo": "group policy",
    "ps": "powershell",
    "ms azure": "microsoft azure",
    "o365": "office 365",
    "ms exchange": "microsoft exchange",
    "exchange online": "microsoft exchange",
    "vm": "virtual machine",
    "vmware vsphere": "vmware",
    "veeam backup": "veeam",
    "dr": "disaster recovery",
    "domain name service": "dns",
    "dynamic host configuration protocol": "dhcp",
    "virtual private network": "vpn",
    "windows server 2003": "windows server",
    "windows server 2008": "windows server",
    "windows server 2012": "windows server",
    "windows server 2016": "windows server",
    "windows server 2019": "windows server",
    "windows server 2022": "windows server",
    "system center configuration manager": "sccm",
    "solar winds": "solarwinds",
    "solaris": "system administration",
    "visual basic script": "vbscript",
    "vbs": "vbscript",
    "command batch": "batch scripting",
    "mcafee anti-virus": "mcafee",
    "mcafee antivirus": "mcafee",
    "anti-virus": "antivirus",
    "hot fix": "patch management",
    "security patch": "patch management",
    "iaas": "cloud computing",
    "saas": "cloud computing",
    "it helpdesk": "help desk",
    "helpdesk": "help desk",
    "tech support": "technical support",
    "koki": "cook",
    "juru masak": "cook",
    "masak": "memasak",
    "memasak makanan": "memasak",
    "dapur": "kitchen",
    "kuliner": "culinary",
    "keamanan pangan": "food safety",
    "kebersihan makanan": "hygiene",
    "persiapan makanan": "food preparation",

    # Modern Frontend
    "nextjs": "next.js",
    "next js": "next.js",
    "nuxtjs": "nuxt",
    "nuxt js": "nuxt",
    "tailwind": "tailwind css",
    "tailwindcss": "tailwind css",

    # Cloud & DevOps
    "amazon web service": "amazon web services",
    "google cloud platform": "gcp",
    "github action": "github actions",
    "continuous integration": "ci/cd",
    "continuous deployment": "ci/cd",
    "continuous delivery": "ci/cd",
    "ci cd": "ci/cd",

    # Agile & PM
    "agile methodology": "agile",
    "scrum methodology": "scrum",
    "manajemen produk": "product management",

    # Data
    "google data studio": "looker",
    "data studio": "looker",
    "apache kafka": "kafka",
    "apache spark": "spark",
    "apache airflow": "airflow",

    # Business & Finance
    "keuangan": "finance",
    "anggaran": "budgeting",
    "perencanaan keuangan": "forecasting",
    "analisis keuangan": "financial analysis",
    "manajemen risiko": "risk management",
    "pengadaan": "procurement",
    "rantai pasok": "supply chain",
    "pergudangan": "warehouse",
    "manajemen inventaris": "inventory",
    "pemasaran digital": "digital marketing",
    "penulisan konten": "content writing",
    "media sosial": "social media",
    "pelatihan": "training",
    "manajemen kinerja": "performance management",
}


# =========================================
# SOFT SKILLS vs TECHNICAL SKILLS
# =========================================
# Soft skills stay visible in extraction, but count less in weighted matching.
SOFT_SKILLS = {
    "time management",
    "problem solving",
    "effective communication",
    "teamwork",
    "collaboration",
    "leadership",
    "communication",
    "interpersonal",
    "adaptability",
    "creativity",
    "critical thinking",
    "organizational",
}

TECHNICAL_SKILLS = {skill for skill in SKILL_LIST if skill not in SOFT_SKILLS}
SOFT_SKILL_WEIGHT_MULTIPLIER = 0.2

FUZZY_MATCH_THRESHOLD = 82
FUZZY_WEIGHT_PENALTY = 0.75

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

# =========================================
# FUZZY MATCHING TARGETS
# =========================================
# Pre-computed list of all canonical skill names plus their aliases.
# Used as the search space for fuzzy matching unrecognised tokens.
_FUZZY_SKILL_TARGETS = sorted(set(SKILL_CANONICALS.keys()), key=len, reverse=True)

# Minimum token length for fuzzy matching — short tokens produce too many
# false positives (e.g. "r" matching "hr").
_FUZZY_MIN_TOKEN_LENGTH = 4


def _levenshtein_distance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def _pure_python_fuzz_ratio(s1, s2):
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 100.0
    dist = _levenshtein_distance(s1, s2)
    return round(((len(s1) + len(s2) - dist) / (len(s1) + len(s2))) * 100, 1)

def fuzzy_match_skill(token, threshold=None):
    """Attempt to match a single token/phrase against the skill database using
    fuzzy string similarity. Returns (canonical_skill, similarity_score) if a
    match is found above the threshold, otherwise None.

    Runs when the rapidfuzz library is available, with pure Python Levenshtein fallback.
    """
    if threshold is None:
        threshold = FUZZY_MATCH_THRESHOLD

    token = token.strip().lower()
    if len(token) < _FUZZY_MIN_TOKEN_LENGTH:
        return None

    if _RAPIDFUZZ_AVAILABLE:
        # Use rapidfuzz process.extractOne for speed — it's implemented in C++
        result = _rprocess.extractOne(
            token,
            _FUZZY_SKILL_TARGETS,
            scorer=_rfuzz.ratio,
            score_cutoff=threshold,
        )

        if result is None:
            return None

        matched_alias, score, _ = result
        canonical = SKILL_LOOKUP.get(matched_alias, matched_alias)
        return (canonical, round(score, 1))
    else:
        # Pure Python Levenshtein fallback
        best_match = None
        best_score = -1

        for target in _FUZZY_SKILL_TARGETS:
            # Quick length filter to optimize speed
            len_diff = abs(len(token) - len(target))
            max_possible_ratio = ((len(token) + len(target) - len_diff) / (len(token) + len(target))) * 100
            if max_possible_ratio < threshold:
                continue

            score = _pure_python_fuzz_ratio(token, target)
            if score >= threshold and score > best_score:
                best_score = score
                best_match = target

        if best_match is None:
            return None

        canonical = SKILL_LOOKUP.get(best_match, best_match)
        return (canonical, round(best_score, 1))

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
    "culinary": [
        "tata boga",
        "kuliner",
        "culinary",
        "culinary arts",
        "food technology",
        "teknologi pangan",
        "gizi",
    ],
    "healthcare": [
        "kedokteran",
        "keperawatan",
        "nursing",
        "farmasi",
        "pharmacy",
        "kesehatan masyarakat",
        "public health",
        "fisioterapi",
        "physiotherapy",
        "kebidanan",
        "midwifery",
    ],
    "legal": [
        "hukum",
        "law",
        "ilmu hukum",
        "legal",
        "notaris",
    ],
    "logistics": [
        "logistik",
        "logistics",
        "supply chain",
        "manajemen logistik",
        "teknik industri",
        "industrial engineering",
        "transportasi",
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
    "culinary": [
        "koki",
        "cook",
        "chef",
        "kitchen",
        "dapur",
        "culinary",
        "kuliner",
        "memasak",
        "masakan",
        "restaurant",
        "restoran",
        "cafe",
        "f&b",
        "food",
        "beverage",
        "barista",
        "pastry",
        "bakery",
    ],
    "healthcare": [
        "dokter",
        "perawat",
        "nurse",
        "apoteker",
        "pharmacist",
        "farmasi",
        "fisioterapi",
        "bidan",
        "klinik",
        "clinic",
        "rumah sakit",
        "hospital",
        "medis",
        "medical",
        "kesehatan",
        "health",
    ],
    "legal": [
        "lawyer",
        "pengacara",
        "legal",
        "hukum",
        "notaris",
        "paralegal",
        "compliance",
        "litigasi",
        "litigation",
    ],
    "logistics": [
        "logistik",
        "logistics",
        "supply chain",
        "warehouse",
        "gudang",
        "kurir",
        "courier",
        "ekspedisi",
        "freight",
        "shipping",
        "procurement",
        "pengadaan",
        "inventory",
        "distribusi",
        "distribution",
    ],
}

EXPERIENCE_SECTION_HEADERS = [
    "pengalaman",
    "pengalaman kerja",
    "experience",
    "work experience",
    "professional experience",
    "job experience",
    "employment history",
    "work history",
    "riwayat kerja",
    "riwayat pekerjaan",
]

# Headers that STOP the experience section when encountered
NON_EXPERIENCE_SECTION_HEADERS = [
    # Education
    "pendidikan",
    "education",
    "riwayat pendidikan",
    "educational background",
    "latar belakang pendidikan",
    # Skills
    "skill",
    "skills",
    "keahlian",
    "kemampuan",
    "technical skills",
    "core skills",
    "competencies",
    "kompetensi",
    # Other common sections
    "projects",
    "project",
    "proyek",
    "portfolio",
    "certifications",
    "certification",
    "sertifikasi",
    "sertifikat",
    "awards",
    "penghargaan",
    "references",
    "referensi",
    "organizations",
    "organisasi",
    "volunteer",
    "languages",
    "bahasa",
    "hobbies",
    "hobi",
    "interests",
    "minat",
    "summary",
    "highlights",
    "objective",
    "profile",
    "profil",
    "about",
    "tentang",
]

# Education degree indicators — lines containing these are education rows, not work
EDUCATION_DEGREE_PATTERN = re.compile(
    r"\b(sma|smk|d1|d2|d3|d4|s1|s2|s3|sarjana|bachelor|master|magister|phd|doctorate|universitas|university|college|institut|institute|akademi|academy|sekolah|school)\b",
    re.IGNORECASE,
)

# Skill-list line: comma/slash-separated list of known tech/soft terms with no duration
SKILL_LIST_LINE_PATTERN = re.compile(
    r"^[\w\s\+\#\.]+(?:[,/][\w\s\+\#\.]+){2,}$"
)

# Pattern: "Position Title  Month YYYY to Month YYYY"  or  "Position  YYYY to YYYY"
# Used for CVs that embed the duration at the end of the position line (no dash separator)
INLINE_DURATION_PATTERN = re.compile(
    r"^(?P<position>.+?)\s+"
    r"(?P<duration>"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?\s*\d{4}\s*(?:to|-)\s*"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)?"
    r"\.?\s*(?:\d{4}|present|current)"
    r"|"
    r"\d{4}\s*(?:to|-)\s*(?:\d{4}|present|current)"
    r")$",
    re.IGNORECASE,
)

# Lines that are clearly job description bullets, not position headers
# - Start with a verb (gerund) like "Installing", "Configuring", "Managing"
# - OR contain only version years like "2003, 2008, 2012" without a range separator
DESCRIPTION_LINE_PATTERN = re.compile(
    r"^(installing|configuring|managing|maintaining|supporting|developing|creating|reviewing|"
    r"troubleshooting|administering|monitoring|scheduling|migrating|collaborating|preparing|"
    r"researching|evaluating|planning|designing|compiling|generating|receiving|debugging|"
    r"participating|communicating|resolving|giving|bertanggung|menggunakan|memimpin|"
    r"mengembangkan|membantu|berkolaborasi|mengelola|melakukan|membuat|memastikan)\b",
    re.IGNORECASE,
)

NON_WORK_ACTIVITY_PATTERN = re.compile(
    r"(@|anggota\s+divisi|koordinator\s+mahasiswa|\bmahasiswa\b|\borganisasi\b|"
    r"\bpanitia\b|\bvolunteer\b|\bbem\b|\bhima\b|\bukm\b)",
    re.IGNORECASE,
)

# A year that appears as a version number (surrounded by commas/spaces, not as a range)
# e.g. "Windows Server 2003, 2008, and 2012" — years with no "to"/"-" range
VERSION_YEAR_ONLY_PATTERN = re.compile(
    r"\b(19|20)\d{2}\b(?!\s*(?:to|-)\s*(?:\d{4}|present|current))"
)

# A valid work entry MUST have a year range somewhere on its header line OR the next line
YEAR_RANGE_PATTERN = re.compile(
    r"\b(19|20)\d{2}\b"
)

# A proper duration range: "2007 to Current", "Aug 2007 to Current", "2007 - 2009",
# "Aug 2007 to Aug 2009", "Aug 2005 to Aug 2007"
YEAR_RANGE_WITH_SEP_PATTERN = re.compile(
    r"\b(19|20)\d{2}\b\s*(?:to|-)\s*"
    r"(?:"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?\s*"
    r")?"
    r"(?:\d{4}|present|current|sekarang|hingga saat ini)",
    re.IGNORECASE,
)

WORK_LEVEL_KEYWORDS = {
    "ceo": 5,
    "director": 5,
    "manager": 4,
    "supervisor": 4,
    "senior": 3,
    "lead": 3,
    "mid level": 2,
    "mid-level": 2,
    "junior": 1,
    "staff": 2,
    "associate": 2,
    "analyst": 2,
    "intern": 0,
    "apprentice": 0,
}

DURATION_PATTERNS = [
    # Month Year - Month Year  (separator: - or to)
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|mei|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\.?\s*(\d{4})\s*(?:-|to)\s*(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|mei|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\.?\s*(\d{4}|present|current|sekarang|hingga saat ini)",
    # Year - Year  or  Year to Year
    r"(\d{4})\s*(?:-|to)\s*(\d{4}|present|current|sekarang|hingga saat ini)",
]


def _infer_work_level(position_text):
    if not position_text or not isinstance(position_text, str):
        return "entry_level"

    normalized = position_text.lower()
    score = 0
    for keyword, weight in WORK_LEVEL_KEYWORDS.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", normalized):
            score = max(score, weight)

    if score >= 4:
        return "senior_manager"
    if score >= 3:
        return "senior"
    if score >= 2:
        return "mid_level"
    if score >= 1:
        return "junior"

    return "entry_level"


def _normalize_duration(duration_text):
    if not duration_text or not isinstance(duration_text, str):
        return ""

    text = duration_text.strip()
    text = re.sub(r"[\u2013\u2014–]", "-", text)
    text = re.sub(r"[\(\)]", "", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    return text


def _parse_duration_interval(duration_text):
    if not duration_text or not isinstance(duration_text, str):
        return None

    text = duration_text.lower()
    text = re.sub(r"[\u2013\u2014–]", "-", text)
    
    # Dynamically use current year — no manual update needed each year
    current_year = datetime.now().year

    for pattern in DURATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            try:
                start_year = int(match.group(1))
            except ValueError:
                continue

            # Check if there's a usable second capture group
            if match.lastindex and match.lastindex >= 2:
                end_value = match.group(2)
            else:
                end_value = None

            if end_value is None:
                end_year = current_year
            elif re.search(r"present|current|sekarang|hingga saat ini", end_value):
                end_year = current_year
            else:
                try:
                    # Clean out any non-numeric residue left in the match group
                    cleaned_end = re.sub(r"\D", "", end_value)
                    end_year = int(cleaned_end) if cleaned_end else current_year
                except ValueError:
                    end_year = current_year

            return (start_year, end_year)

    return None


def _parse_duration_years(duration_text):
    interval = _parse_duration_interval(duration_text)
    if interval:
        return max(0, interval[1] - interval[0])
    return 0


def _is_experience_header(line):
    """Return True only if the line IS an experience section header (exact/standalone match)."""
    stripped = line.strip().lower().rstrip(":")
    return stripped in EXPERIENCE_SECTION_HEADERS


def _is_stop_header(line):
    """Return True if the line is a standalone NON-experience section header."""
    stripped = line.strip().lower().rstrip(":")
    return stripped in NON_EXPERIENCE_SECTION_HEADERS


def _is_education_line(line):
    """Return True if the line looks like an education entry (degree, university, etc.)."""
    return bool(EDUCATION_DEGREE_PATTERN.search(line))


def _is_skill_list_line(line):
    """Return True if the line looks like a comma/slash separated skill list."""
    stripped = line.strip()
    # Must have 2+ separators and no year range
    if not SKILL_LIST_LINE_PATTERN.match(stripped):
        return False
    if YEAR_RANGE_PATTERN.search(stripped):
        return False
    return True


def _has_year(line):
    return bool(YEAR_RANGE_PATTERN.search(line))


def _has_year_range(line):
    """Return True only if line contains a proper year range (year + to/- + year/present)."""
    return bool(YEAR_RANGE_WITH_SEP_PATTERN.search(line))


def _is_description_line(line):
    """Return True if line is a job description bullet (starts with action verb)."""
    return bool(DESCRIPTION_LINE_PATTERN.match(line.strip()))


def _is_non_work_activity_line(line):
    return bool(NON_WORK_ACTIVITY_PATTERN.search(line or ""))


def extract_work_experience(text):
    if not text or not isinstance(text, str):
        return []

    lines = [line.rstrip() for line in text.splitlines()]

    # ── 1. Locate the experience section ──────────────────────────────────────
    start_index = next(
        (
            idx
            for idx, line in enumerate(lines)
            if _is_experience_header(line)
        ),
        None,
    )

    if start_index is None:
        # No explicit section header found — cannot safely guess boundaries
        return []

    # ── 2. Collect lines ONLY inside the experience section ───────────────────
    section_lines = []
    for line in lines[start_index + 1 :]:
        normalized = line.strip()

        # Stop at any other section header (education, skills, projects, …)
        if _is_stop_header(normalized):
            break

        # Also stop if we hit another experience section header
        if _is_experience_header(normalized):
            break

        # Skip blank lines (don't count them as terminators)
        if not normalized:
            continue

        # Drop education lines that slipped through
        if _is_education_line(normalized):
            continue

        # Drop plain skill-list lines
        if _is_skill_list_line(normalized):
            continue

        section_lines.append(line)

    # ── 3. Parse entries from section_lines ───────────────────────────────────
    position_company_pattern = re.compile(
        r"^(?P<position>.+?)\s*[-–—]\s*(?P<company>.+?)(?:\s*\((?P<duration>[^)]+)\))?$",
    )
    fallback_pattern = re.compile(
        r"^(?P<position>.+?)(?:\s+at\s+|\s+@\s+|,\s*)(?P<company>.+?)(?:\s*\((?P<duration>[^)]+)\))?$",
        re.IGNORECASE,
    )

    experiences = []

    for index, line in enumerate(section_lines):
        stripped = line.strip().lstrip("*-• ").strip()
        if not stripped:
            continue

        # Skip lines that are clearly job description bullets
        if _is_description_line(stripped):
            continue

        if _is_non_work_activity_line(stripped):
            continue

        if re.match(r"^(19|20)\d{2}\s*(?:-|to)\s*(?:\d{4}|present|current|sekarang)\b", stripped, re.IGNORECASE):
            continue

        # Must contain a proper year RANGE (year + to/- + year/present) on this line
        # OR the immediately following line must have a year range.
        # A bare year (e.g. "Windows Server 2003") does NOT qualify.
        line_has_range = _has_year_range(stripped)
        next_has_range = (
            index + 1 < len(section_lines)
            and _has_year_range(section_lines[index + 1])
        )
        if not line_has_range and not next_has_range:
            continue

        position = ""
        company = ""
        duration = ""

        # ── Format B (try first): "Position Title  Aug 2007 to Current"  ────────
        # Try inline before dash-separator patterns because a comma in the position
        # (e.g. "Liaison, T") would confuse the fallback_pattern.
        inline_match = INLINE_DURATION_PATTERN.match(stripped) if line_has_range else None

        if inline_match:
            position = inline_match.group("position").strip()
            duration = inline_match.group("duration").strip()

            # Company is on the next line (skip encoding artifacts like ï¼​)
            if index + 1 < len(section_lines):
                next_line = section_lines[index + 1].strip()
                next_line = re.sub(r"[^\x00-\x7F]+", " ", next_line).strip()
                # Take only the company part (before city/state after comma)
                company = next_line.split(",")[0].strip()

        else:
            # ── Format A: "Position - Company (duration)" ─────────────────────
            match = position_company_pattern.match(stripped)
            if not match:
                match = fallback_pattern.match(stripped)

            if match:
                position = match.group("position").strip()
                company  = match.group("company").strip()
                duration = match.group("duration") or ""

                # Look for duration on the next line if not embedded
                if not duration and index + 1 < len(section_lines):
                    next_line = section_lines[index + 1].strip()
                    if _has_year_range(next_line):
                        duration = next_line

        if not position or not company:
            continue

        duration = _normalize_duration(duration)

        # Guard: position must not look like an education entry
        if _is_education_line(position) or _is_education_line(company):
            continue

        if _is_non_work_activity_line(position) or _is_non_work_activity_line(company):
            continue

        # Guard: position must not be a bare skill name or very short token list
        if _is_skill_list_line(position):
            continue

        # Guard: both position and company must be non-trivial (at least 2 chars each)
        if len(position) < 2 or len(company) < 2:
            continue

        experiences.append(
            {
                "position": position,
                "company": company,
                "duration": duration,
                "level": _infer_work_level(position),
                "description": "",
            }
        )

    return experiences


def calculate_total_experience_years(work_experiences):
    if not work_experiences or not isinstance(work_experiences, list):
        return 0

    intervals = []
    for item in work_experiences:
        duration = item.get("duration", "") if isinstance(item, dict) else ""
        if duration:
            interval = _parse_duration_interval(duration)
            if interval:
                intervals.append(interval)

    if not intervals:
        return 0

    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    merged = []
    for interval in intervals:
        if not merged or merged[-1][1] < interval[0]:
            merged.append(interval)
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], interval[1]))

    total_years = sum(end - start for start, end in merged)
    return total_years


def get_experience_level_match(cv_experience_level, job_title):
    level_rank = {
        "entry_level": 0,
        "junior": 1,
        "mid_level": 2,
        "senior": 3,
        "senior_manager": 4,
    }

    cv_level = cv_experience_level if isinstance(cv_experience_level, str) else "entry_level"
    cv_score = level_rank.get(cv_level, 0)
    job_score = level_rank.get(_infer_work_level(job_title), 0)

    if job_score == 0:
        return 1.0
    if cv_score >= job_score:
        return 1.0

    return max(0.3, cv_score / job_score)


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
def _extract_fuzzy_tokens(cleaned_text, already_matched):
    """Extract candidate tokens from cleaned text for fuzzy matching.
    Splits on whitespace and also tries bi-gram phrases (e.g. 'node js').
    Only returns tokens that are NOT already matched by exact regex."""
    words = cleaned_text.split()
    candidates = set()

    # Single word tokens
    for word in words:
        if len(word) >= _FUZZY_MIN_TOKEN_LENGTH and word not in already_matched:
            candidates.add(word)

    # Bi-gram phrases (for multi-word skills like 'node.js', 'data analysis')
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        if bigram not in already_matched:
            candidates.add(bigram)

    return candidates


def extract_skills(text, include_soft_skills=True, fuzzy=True):

    if not text:
        return []

    cleaned_text = clean_text(text)

    found_skills = set()
    match_types = {}  # skill -> "exact" | "fuzzy"

    # ── Pass 1: Exact regex matching (original behaviour) ──
    matched_spans = set()
    for match in SKILL_ALIAS_PATTERN.finditer(cleaned_text):
        skill = SKILL_LOOKUP[match.group(1)]
        if include_soft_skills or skill not in SOFT_SKILLS:
            found_skills.add(skill)
            match_types[skill] = "exact"
            matched_spans.add(match.group(1))

    # ── Pass 2: Fuzzy matching for unrecognised tokens ──
    if fuzzy:  # Runs always using rapidfuzz or Python Levenshtein fallback
        candidates = _extract_fuzzy_tokens(cleaned_text, matched_spans)
        for token in candidates:
            if token in matched_spans:
                continue
            result = fuzzy_match_skill(token)
            if result:
                canonical, _score = result
                if canonical not in found_skills:
                    if include_soft_skills or canonical not in SOFT_SKILLS:
                        found_skills.add(canonical)
                        match_types[canonical] = "fuzzy"

    # =====================================
    # SORTING: technical skills first, then soft skills
    # =====================================
    technical = sorted(skill for skill in found_skills if skill not in SOFT_SKILLS)
    soft = sorted(skill for skill in found_skills if skill in SOFT_SKILLS)
    return technical + soft


def extract_skills_with_types(text, include_soft_skills=True):
    """Like extract_skills but also returns match type metadata.
    Returns (skills_list, match_types_dict)."""
    if not text:
        return [], {}

    cleaned_text = clean_text(text)

    found_skills = set()
    match_types = {}

    matched_spans = set()
    for match in SKILL_ALIAS_PATTERN.finditer(cleaned_text):
        skill = SKILL_LOOKUP[match.group(1)]
        if include_soft_skills or skill not in SOFT_SKILLS:
            found_skills.add(skill)
            match_types[skill] = "exact"
            matched_spans.add(match.group(1))

    if True:  # Runs always using rapidfuzz or Python Levenshtein fallback
        candidates = _extract_fuzzy_tokens(cleaned_text, matched_spans)
        for token in candidates:
            if token in matched_spans:
                continue
            result = fuzzy_match_skill(token)
            if result:
                canonical, _score = result
                if canonical not in found_skills:
                    if include_soft_skills or canonical not in SOFT_SKILLS:
                        found_skills.add(canonical)
                        match_types[canonical] = "fuzzy"

    technical = sorted(skill for skill in found_skills if skill not in SOFT_SKILLS)
    soft = sorted(skill for skill in found_skills if skill in SOFT_SKILLS)
    return technical + soft, match_types


def extract_technical_skills(text):
    return extract_skills(text, include_soft_skills=False)


def extract_weighted_skills(text):
    """Extract skills with frequency + context weights.
    Returns (weighted_skills_dict, match_types_dict)."""
    if not text:
        return {}, {}

    cleaned_text = clean_text(text)
    skill_counts = Counter()
    context_bonus = Counter()
    match_types = {}

    # ── Pass 1: Exact regex matching ──
    matched_spans = set()
    for match in SKILL_ALIAS_PATTERN.finditer(cleaned_text):
        canonical_skill = SKILL_LOOKUP[match.group(1)]
        skill_counts[canonical_skill] += 1
        match_types[canonical_skill] = "exact"
        matched_spans.add(match.group(1))

        left = max(0, match.start() - 80)
        right = min(len(cleaned_text), match.end() + 80)
        context = cleaned_text[left:right]
        if any(keyword in context for keyword in CONTEXT_KEYWORDS):
            context_bonus[canonical_skill] += 1

    # ── Pass 2: Fuzzy matching for unrecognised tokens ──
    if True:  # Runs always using rapidfuzz or Python Levenshtein fallback
        candidates = _extract_fuzzy_tokens(cleaned_text, matched_spans)
        for token in candidates:
            if token in matched_spans:
                continue
            result = fuzzy_match_skill(token)
            if result:
                canonical, _score = result
                if canonical not in skill_counts:
                    skill_counts[canonical] = 1
                    match_types[canonical] = "fuzzy"

    weighted_skills = {}
    for skill, count in skill_counts.items():
        frequency_weight = 1.0 + min(1.2, (count - 1) * 0.35)
        context_weight = min(0.8, context_bonus[skill] * 0.25)
        raw_weight = round(min(MAX_SKILL_WEIGHT, frequency_weight + context_weight), 3)
        if skill in SOFT_SKILLS:
            raw_weight = round(raw_weight * SOFT_SKILL_WEIGHT_MULTIPLIER, 3)
        # Apply fuzzy penalty — fuzzy matches get reduced confidence
        if match_types.get(skill) == "fuzzy":
            raw_weight = round(raw_weight * FUZZY_WEIGHT_PENALTY, 3)
        weighted_skills[skill] = raw_weight

    sorted_skills = dict(sorted(weighted_skills.items(), key=lambda item: (-item[1], item[0])))
    return sorted_skills, match_types


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
# GEMINI LLM RESUME PARSER
# =========================================
import json
import logging
import os

logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, Field
    from typing import List, Optional

    class WorkExperienceItem(BaseModel):
        role: str = Field(description="Role or job title, e.g. 'Frontend Developer'")
        years: float = Field(description="Duration in years, e.g. 2.5 or 1.0")
        company: str = Field(description="Company name")
        duration: str = Field(description="Duration string, e.g. 'Jan 2021 - Jun 2023'")

    class EducationItem(BaseModel):
        degree: str = Field(description="Degree, e.g. 'Bachelor', 'Master', 'Diploma' or 'High School'")
        major: str = Field(description="Major or field of study, e.g. 'Computer Science'")
        institution: str = Field(description="School or university name")

    class GeminiResumeProfile(BaseModel):
        skills: List[str] = Field(description="List of technical and soft skills extracted from the resume")
        work_experiences: List[WorkExperienceItem] = Field(description="List of work experiences")
        education: List[EducationItem] = Field(description="List of education history")
        summary: str = Field(description="A short, professional summary of the candidate's profile")
        improvements: List[str] = Field(description="3-4 specific action items, e.g. recommended online courses (from platforms like Dicoding/Coursera), technical portfolio projects to build, or precise CV phrasing corrections to close their skill gap for the target role.")

    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False


def extract_profile_with_gemini(text, target_role=None):
    """
    Extract technical skills, experiences, and education profiles using Gemini API.
    Also generates highly personalized roadmap improvements if target_role is provided.
    Provides a seamless fallback to the local regex parser if GEMINI_API_KEY is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.info("GEMINI_API_KEY is not configured. Falling back to local parser.")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        You are an expert ATS (Applicant Tracking System) parser and elite career coach. 
        Extract the following information from the resume text:
        - Skills (both technical and soft skills)
        - Work Experience (roles, years of experience, companies, durations)
        - Education Profile (degrees, majors, institutions)
        - A brief professional summary (MUST be written in Indonesian language / Bahasa Indonesia)
        """
        
        if target_role:
            prompt += f"""
            - 3-4 highly specific, personalized improvements and concrete roadmap steps for their target role: '{target_role}'. (MUST be written in Indonesian language / Bahasa Indonesia).
            This should include recommended online courses (prioritizing Indonesian platform 'Dicoding' or global 'Coursera/Udemy'), specific projects to build, or exact CV phrasing changes to close the skill gap.
            """
        else:
            prompt += """
            - List 3 general CV improvements to make their resume stand out (MUST be written in Indonesian language / Bahasa Indonesia).
            """
            
        prompt += f"""
        IMPORTANT: All human-readable output text fields (specifically 'summary' and the items in 'improvements') MUST be written in fluent, professional Indonesian language (Bahasa Indonesia).
        
        Resume text:
        {text}
        """
        
        if _PYDANTIC_AVAILABLE:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiResumeProfile,
                ),
            )
            result = json.loads(response.text)
            logger.info("Successfully parsed resume using Gemini API.")
            return result
        else:
            fallback_schema = "{'skills': [str], 'work_experiences': [{'role': str, 'years': float, 'company': str, 'duration': str}], 'education': [{'degree': str, 'major': str, 'institution': str}], 'summary': str, 'improvements': [str]}"
            response = model.generate_content(
                prompt + f"\nFormat the output strictly as a JSON object matching this schema: {fallback_schema}",
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                ),
            )
            result = json.loads(response.text)
            logger.info("Successfully parsed resume using Gemini API (JSON fallback).")
            return result
            
    except Exception as e:
        logger.warning("Gemini parsing failed, falling back to local NLP parser: %s", str(e))
        return None


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
