import copy
import hashlib
import json
import logging
import math
import time
import uuid
from collections import Counter
from functools import lru_cache

from modules import jobs_service
from modules.config import AUTO_MAX_CANDIDATE_JOBS, MAX_CANDIDATE_JOBS, MIN_EXTRACTED_TEXT_LENGTH, TOP_K
from modules.cv_parser import extract_text_from_pdf
from modules.nlp import (
    NLP_CACHE_VERSION,
    calculate_total_experience_years,
    clean_text,
    extract_education_profile,
    extract_skills,
    extract_weighted_skills,
    extract_work_experience,
    get_experience_level_match,
    extract_profile_with_gemini,
    SOFT_SKILLS,
    MAX_SKILL_WEIGHT,
)


logger = logging.getLogger("jobfit.analysis")
SCORING_CACHE_VERSION = "rule-bm25-core-gate-v4-2026-06-04"


def log_analysis_stage(timings, stage, started_at):
    elapsed = time.perf_counter() - started_at
    timings[stage] = elapsed
    logger.info("Analysis stage %s completed in %.2fs", stage, elapsed)

TARGET_ROLE_SYNONYMS = {
    "koki": {"cook", "chef", "kitchen", "dapur", "culinary", "kuliner", "memasak", "masak"},
    "juru": {"cook", "chef", "kitchen", "dapur", "culinary"},
    "masak": {"cook", "chef", "kitchen", "dapur", "culinary"},
    "memasak": {"cook", "chef", "kitchen", "dapur", "culinary"},
    "chef": {"koki", "cook", "kitchen", "dapur", "culinary"},
    "cook": {"koki", "chef", "kitchen", "dapur", "culinary"},
    "dapur": {"koki", "cook", "chef", "kitchen", "culinary"},
}

ROLE_FAMILIES = {
    "frontend": {
        "frontend", "front-end", "react", "vue", "angular", "html", "css", "ui", "web ui",
        "javascript", "typescript", "next.js", "tailwind",
    },
    "backend": {
        "backend", "back-end", "api", "server", "node", "express", "fastapi", "django",
        "flask", "laravel", "database", "postgresql", "mysql",
    },
    "fullstack": {
        "fullstack", "full stack", "full-stack", "frontend", "backend", "web developer",
        "software developer",
    },
    "data": {
        "data analyst", "data scientist", "machine learning engineer", "ai engineer",
        "data science", "machine learning", "data", "analyst", "analytics",
        "business intelligence", "dashboard", "sql", "python", "excel", "etl",
        "visualization", "statistics", "clustering", "classification",
    },
    "finance": {
        "finance", "accounting", "akuntansi", "tax", "pajak", "invoice", "payable",
        "receivable", "rekonsiliasi", "keuangan",
    },
    "admin": {
        "admin", "administrative", "administration", "data entry", "filing", "scheduling",
        "office", "dokumen", "surat",
    },
    "hr": {
        "hr", "human resources", "recruiter", "recruitment", "talent", "interview",
        "screening", "onboarding", "hiring",
    },
    "sales": {
        "sales", "marketing", "business development", "account executive", "crm",
        "prospect", "customer relationship", "negotiation",
    },
    "design": {
        "designer", "graphic", "creative", "visual", "figma", "photoshop",
        "illustrator", "branding", "typography",
    },
    "operator": {
        "operator", "production", "manufacturing", "machine operator", "quality control",
        "packing", "pabrik", "shift", "k3",
    },
    "culinary": {
        "chef", "cook", "koki", "dapur", "kitchen", "culinary", "memasak", "tata boga",
        "food", "restaurant", "f&b",
    },
    "sports": {
        "pemain bola", "sepak bola", "football", "soccer", "athlete", "atlet", "coach",
        "pelatih", "futsal", "olahraga", "sport",
    },
    "education": {
        "teacher", "guru", "dosen", "tutor", "pengajar", "education", "pendidikan",
        "kindergarten", "preschool",
    },
    "healthcare": {
        "doctor", "dokter", "nurse", "perawat", "farmasi", "pharmacist", "bidan",
        "medical", "healthcare", "klinik", "rumah sakit",
    },
    "legal": {
        "legal", "law", "hukum", "lawyer", "pengacara", "notaris", "paralegal",
        "compliance",
    },
    "hospitality": {
        "hotel", "hospitality", "front office", "housekeeping", "receptionist",
        "guest service", "tour guide", "pemandu wisata",
    },
    "logistics": {
        "logistics", "logistik", "warehouse", "gudang", "kurir", "driver", "supir",
        "delivery", "shipping", "inventory",
    },
    "security": {
        "security", "satpam", "guard", "keamanan", "safety officer",
    },
}

ROLE_COMPATIBILITY = {
    ("frontend", "fullstack"),
    ("backend", "fullstack"),
    ("fullstack", "frontend"),
    ("fullstack", "backend"),
    ("data", "admin"),
    ("admin", "data"),
    ("finance", "admin"),
    ("sales", "admin"),
    ("design", "sales"),
    ("operator", "engineering"),
    ("hospitality", "culinary"),
    ("culinary", "hospitality"),
    ("logistics", "operator"),
    ("operator", "logistics"),
}

DOMAIN_TO_ROLE_FAMILY = {
    "it": {"frontend", "backend", "fullstack"},
    "data_ai": {"data"},
    "finance": {"finance"},
    "business": {"admin", "sales", "hr"},
    "design": {"design"},
    "logistics": {"operator", "admin"},
    "culinary": {"culinary"},
    "healthcare": {"healthcare"},
    "legal": {"legal"},
    "hospitality": {"hospitality"},
}

ROLE_RISK_MESSAGES = {
    "role_family_mismatch": "Role lowongan berbeda jauh dari target atau sinyal utama CV.",
    "seniority_mismatch": "Level lowongan terlihat lebih tinggi dari pengalaman yang terbaca.",
    "weak_skill_evidence": "Skill inti lowongan belum cukup kuat muncul di CV.",
    "core_role_evidence_missing": "Bukti skill inti untuk role target belum cukup kuat.",
    "generic_skill_only_match": "Kecocokan terutama berasal dari skill umum, bukan bukti role-specific.",
}

ROLE_FAMILY_TERM_CACHE = None

CORE_ROLE_SKILLS = {
    "frontend": {"html", "css", "javascript", "react", "vue", "angular", "typescript", "next.js", "ui ux"},
    "backend": {"python", "node.js", "fastapi", "django", "laravel", "rest api", "database", "postgresql", "mysql", "docker"},
    "fullstack": {"javascript", "react", "node.js", "database", "rest api", "html", "css", "git"},
    "admin": {"administration", "administrative", "data entry", "filing", "scheduling", "microsoft office", "excel"},
    "hr": {"recruitment", "interview", "screening", "onboarding", "human resources", "employee database"},
    "sales": {"sales", "marketing", "crm", "negotiation", "prospect", "customer relationship", "presentation"},
    "design": {"photoshop", "illustrator", "branding", "typography", "ui ux", "graphic design"},
    "operator": {"production operator", "machine operator", "quality control", "k3", "packing"},
    "culinary": {
        "cook", "memasak", "kitchen", "food preparation", "food safety", "hygiene",
        "tata boga", "chef",
    },
    "education": {"teacher", "guru", "tutor", "pengajar", "lesson", "teaching", "training"},
    "healthcare": {"medical", "doctor", "nurse", "farmasi", "bidan", "healthcare"},
    "legal": {"legal", "law", "hukum", "lawyer", "compliance"},
    "finance": {"finance", "accounting", "tax", "invoice", "reconciliation"},
    "data": {"sql", "python", "data visualization", "statistics", "dashboard"},
    "hospitality": {"hospitality", "hotel", "front office", "housekeeping", "guest service", "receptionist"},
    "logistics": {"logistics", "warehouse", "inventory", "shipping", "delivery", "stock opname", "gudang"},
    "security": {"security", "satpam", "guard", "keamanan", "safety officer"},
    "sports": {"football", "soccer", "pemain bola", "atlet", "athlete", "futsal", "coach", "pelatih"},
}

GENERAL_SUPPORT_SKILLS = {
    "excel", "microsoft office", "word", "powerpoint", "communication", "teamwork",
    "time management", "administration", "administrative", "problem solving",
    "leadership", "collaboration", "finance", "budgeting", "data entry",
}

STRICT_CORE_FAMILIES = {
    "healthcare", "legal", "education", "security", "sports", "operator", "design",
}

SPECIFIC_AUTO_FAMILIES = {
    "backend", "data", "design", "finance", "frontend", "fullstack", "hr",
    "legal", "logistics", "operator", "sales",
}

COURSE_RECOMMENDATION_SKILL_ALLOWLIST = {
    "frontend": {
        "html", "css", "javascript", "typescript", "react", "vue", "angular", "next.js",
        "tailwind", "git", "rest api", "figma", "ui ux",
    },
    "backend": {
        "python", "node.js", "express", "laravel", "fastapi", "django", "flask",
        "rest api", "git", "docker", "sql", "postgresql", "mysql", "mongodb",
    },
    "fullstack": {
        "html", "css", "javascript", "typescript", "react", "node.js", "rest api",
        "git", "docker", "sql", "postgresql", "mysql",
    },
    "data": {
        "python", "sql", "excel", "pandas", "data analysis", "statistics",
        "power bi", "tableau", "machine learning",
    },
    "finance": {"excel", "accounting", "finance"},
    "admin": {"excel", "data entry", "customer service", "project management"},
    "hr": {"human resources", "recruitment", "customer service"},
    "sales": {"digital marketing", "seo", "copywriting", "crm", "customer service"},
    "design": {"figma", "ui ux", "photoshop", "illustrator", "branding"},
    "operator": {"quality control", "k3", "project management"},
    "culinary": {"cooking", "food safety", "hygiene"},
    "hospitality": {"housekeeping", "hotel management", "customer service"},
    "logistics": {"logistics", "warehouse", "excel"},
    "security": {"k3"},
}

NEGATIVE_CONTEXT_MARKERS = {
    "tidak punya", "tidak memiliki", "belum memiliki", "belum punya", "bukan",
    "tanpa pengalaman", "tidak menggunakan", "belum menggunakan", "tidak menguasai",
    "no experience", "not using", "without experience", "not familiar",
}

ROADMAP_TEMPLATES = {
    "frontend": {
        "skills": ["html", "css", "javascript", "react", "git", "rest api"],
        "projects": [
            "Buat portfolio web responsif dengan 3 halaman dan deploy online.",
            "Bangun dashboard sederhana memakai React, data dummy, filter, dan chart.",
            "Tulis studi kasus project: masalah, stack, fitur, dan hasil yang dicapai.",
        ],
    },
    "backend": {
        "skills": ["python", "node.js", "database", "rest api", "docker", "unit testing"],
        "projects": [
            "Bangun REST API CRUD lengkap dengan auth dan validasi input.",
            "Tambahkan database PostgreSQL/MySQL dan dokumentasi endpoint.",
            "Buat test sederhana dan catat performa response sebelum-sesudah optimasi.",
        ],
    },
    "fullstack": {
        "skills": ["javascript", "react", "node.js", "database", "rest api", "git"],
        "projects": [
            "Bangun aplikasi fullstack kecil dari login sampai dashboard.",
            "Pisahkan frontend/backend dan tulis README setup lokal.",
            "Tambahkan fitur deploy dan screenshot hasil aplikasi.",
        ],
    },
    "data": {
        "skills": ["sql", "excel", "python", "dashboard", "statistics", "data visualization"],
        "projects": [
            "Analisis dataset publik dan buat insight bisnis dengan grafik.",
            "Buat dashboard Excel/Power BI sederhana dengan filter.",
            "Tulis narasi insight: pertanyaan, metode, temuan, dan rekomendasi.",
        ],
    },
    "admin": {
        "skills": ["excel", "data entry", "administration", "customer service", "filing"],
        "projects": [
            "Buat template laporan administrasi dan rekap data di Excel.",
            "Tulis contoh SOP pengarsipan dokumen atau pelayanan pelanggan.",
            "Tambahkan pencapaian berbasis angka seperti jumlah data/dokumen yang dikelola.",
        ],
    },
    "finance": {
        "skills": ["excel", "accounting", "finance", "tax", "invoice", "reconciliation"],
        "projects": [
            "Buat contoh laporan kas sederhana dengan rumus Excel.",
            "Susun simulasi invoice dan rekonsiliasi bank.",
            "Tuliskan pengalaman administrasi angka dengan akurasi dan deadline.",
        ],
    },
    "design": {
        "skills": ["figma", "photoshop", "illustrator", "branding", "typography"],
        "projects": [
            "Buat 3 desain social media dalam satu campaign.",
            "Susun mini brand guideline: warna, font, logo usage, dan contoh layout.",
            "Tampilkan before-after desain dan alasan keputusan visual.",
        ],
    },
    "sales": {
        "skills": ["sales", "marketing", "crm", "negotiation", "presentation"],
        "projects": [
            "Buat contoh pipeline prospect dan laporan penjualan mingguan.",
            "Tulis simulasi campaign sederhana dengan target audience dan KPI.",
            "Tambahkan angka target, conversion, atau jumlah pelanggan yang ditangani.",
        ],
    },
    "hr": {
        "skills": ["recruitment", "interview", "screening", "onboarding", "communication"],
        "projects": [
            "Buat template screening kandidat dan scorecard interview.",
            "Tulis alur onboarding sederhana untuk karyawan baru.",
            "Cantumkan jumlah kandidat, posisi, atau proses hiring yang pernah dibantu.",
        ],
    },
    "operator": {
        "skills": ["production operator", "machine operator", "quality control", "k3"],
        "projects": [
            "Tulis pengalaman kerja shift, target output, dan standar keselamatan.",
            "Buat contoh checklist kualitas produksi atau perawatan mesin.",
            "Tambahkan metrik seperti output harian, error rate, atau kepatuhan SOP.",
        ],
    },
    "culinary": {
        "skills": ["cook", "kitchen", "food preparation", "hygiene", "food safety"],
        "projects": [
            "Buat portfolio menu dengan foto, bahan, dan proses singkat.",
            "Tulis pengalaman menjaga kebersihan dapur dan standar food safety.",
            "Cantumkan jumlah porsi, jenis menu, atau ritme kerja service yang pernah ditangani.",
        ],
    },
    "sports": {
        "skills": ["training", "teamwork", "match analysis", "fitness", "coaching"],
        "projects": [
            "Cantumkan posisi, klub/sekolah, turnamen, dan capaian yang pernah diikuti.",
            "Tulis rutinitas latihan, peran di tim, dan indikator performa yang bisa dibuktikan.",
            "Tambahkan sertifikat kepelatihan, lisensi, atau dokumentasi pertandingan bila ada.",
        ],
    },
    "education": {
        "skills": ["teaching", "lesson planning", "classroom management", "assessment", "communication"],
        "projects": [
            "Buat contoh RPP/modul ajar singkat sesuai target kelas atau mata pelajaran.",
            "Tulis pengalaman mengajar, mentoring, atau asistensi dengan jumlah peserta dan hasilnya.",
            "Tambahkan bukti evaluasi belajar seperti pre-test/post-test, rubrik, atau feedback siswa.",
        ],
    },
    "healthcare": {
        "skills": ["patient care", "medical", "clinical documentation", "hygiene", "healthcare"],
        "projects": [
            "Cantumkan praktik klinik, sertifikasi, STR/SIP bila relevan, dan unit layanan yang pernah ditangani.",
            "Tulis pengalaman mengikuti SOP keselamatan pasien, dokumentasi medis, atau edukasi pasien.",
            "Tambahkan contoh kasus non-rahasia dengan tindakan, koordinasi, dan hasil perawatan.",
        ],
    },
    "legal": {
        "skills": ["legal research", "drafting", "compliance", "contract review", "case analysis"],
        "projects": [
            "Buat contoh legal memo, ringkasan regulasi, atau analisis kontrak non-rahasia.",
            "Tulis pengalaman riset hukum, administrasi perkara, review dokumen, atau kepatuhan.",
            "Cantumkan bidang hukum, tools riset, dan output yang pernah dibuat.",
        ],
    },
    "hospitality": {
        "skills": ["guest service", "front office", "housekeeping", "reservation", "complaint handling"],
        "projects": [
            "Tulis pengalaman melayani tamu, menangani reservasi, atau menyelesaikan komplain.",
            "Cantumkan standar layanan, jumlah tamu/kamar/meja, shift, dan hasil kepuasan pelanggan.",
            "Tambahkan bukti bahasa, grooming, atau sertifikasi hospitality bila ada.",
        ],
    },
    "logistics": {
        "skills": ["inventory", "warehouse", "shipping", "delivery", "stock control"],
        "projects": [
            "Tulis pengalaman mengelola stok, picking-packing, pengiriman, atau administrasi gudang.",
            "Cantumkan volume barang, akurasi stok, waktu proses, dan tools yang dipakai.",
            "Buat contoh checklist inbound/outbound atau laporan stok sederhana.",
        ],
    },
    "security": {
        "skills": ["security", "safety", "surveillance", "incident reporting", "access control"],
        "projects": [
            "Cantumkan pengalaman pengamanan area, patroli, kontrol akses, atau laporan insiden.",
            "Tulis standar keselamatan, shift, area tanggung jawab, dan koordinasi saat kejadian.",
            "Tambahkan sertifikasi satpam, K3, atau pelatihan keamanan bila ada.",
        ],
    },
}

ROLE_ACTION_EXAMPLES = {
    "frontend": "Contoh: 'Membangun halaman web responsif dengan JavaScript dan CSS sehingga proses pendaftaran lebih mudah dipakai'.",
    "backend": "Contoh: 'Membangun API atau alur database untuk mempercepat proses input dan pencarian data'.",
    "fullstack": "Contoh: 'Membuat aplikasi web dari form input sampai dashboard laporan dengan alur pengguna yang jelas'.",
    "data": "Contoh: 'Menganalisis dataset dan membuat dashboard insight yang membantu pengambilan keputusan'.",
    "admin": "Contoh: 'Mengelola dokumen dan rekap data harian dengan Excel sehingga laporan lebih rapi dan cepat dicek'.",
    "finance": "Contoh: 'Membantu pencatatan transaksi dan rekonsiliasi sederhana dengan akurasi yang terukur'.",
    "design": "Contoh: 'Membuat materi visual campaign dengan brief, revisi, dan hasil desain yang terdokumentasi'.",
    "sales": "Contoh: 'Menghubungi prospek, mencatat follow-up, dan membantu meningkatkan jumlah lead yang diproses'.",
    "hr": "Contoh: 'Membantu screening kandidat, menjadwalkan interview, dan merapikan data pelamar'.",
    "operator": "Contoh: 'Menjalankan proses produksi sesuai SOP, menjaga kualitas output, dan melaporkan kendala shift'.",
    "culinary": "Contoh: 'Menyiapkan bahan, menjaga kebersihan dapur, dan membantu service untuk sejumlah porsi/menu'.",
    "sports": "Contoh: 'Mengikuti program latihan rutin, berperan dalam tim, dan mencatat capaian pertandingan/turnamen'.",
    "education": "Contoh: 'Menyusun materi ajar, mendampingi peserta belajar, dan mengevaluasi progres dengan feedback'.",
    "healthcare": "Contoh: 'Membantu dokumentasi klinis, edukasi pasien, atau prosedur layanan sesuai SOP kesehatan'.",
    "legal": "Contoh: 'Menyusun ringkasan regulasi, melakukan riset hukum, atau membantu review dokumen non-rahasia'.",
    "hospitality": "Contoh: 'Melayani tamu, menangani reservasi/komplain, dan menjaga standar layanan selama shift'.",
    "logistics": "Contoh: 'Mengelola stok, menyiapkan pengiriman, dan menjaga akurasi data barang masuk-keluar'.",
    "security": "Contoh: 'Melakukan patroli, kontrol akses, dan membuat laporan insiden sesuai prosedur keamanan'.",
}


def get_match_level(score):
    if score >= 80:
        return "Kecocokan Sangat Tinggi"
    if score >= 60:
        return "Kecocokan Tinggi"
    if score >= 40:
        return "Kecocokan Sedang"
    if score >= 20:
        return "Kecocokan Rendah"
    return "Kecocokan Sangat Rendah"


def tokenize(text):
    return jobs_service.tokenize(text)


def token_set(text):
    return jobs_service.token_set(text)


def overlap_score(left, right):
    left_tokens = token_set(left)
    right_tokens = token_set(right)

    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens)


EXPANDED_TOKENS_CACHE = {}


def expanded_target_tokens(target_role):
    if target_role not in EXPANDED_TOKENS_CACHE:
        tokens = token_set(target_role)
        expanded = set(tokens)

        for token in tokens:
            expanded.update(TARGET_ROLE_SYNONYMS.get(token, set()))
        EXPANDED_TOKENS_CACHE[target_role] = expanded

    return EXPANDED_TOKENS_CACHE[target_role]


def target_role_overlap(target_role, text):
    base_tokens = token_set(target_role)
    right_tokens = token_set(text)

    if not base_tokens or not right_tokens:
        return 0.0

    target_clean = clean_text(target_role)
    right_clean = clean_text(text)
    if "machine learning" in target_clean:
        ml_markers = {
            "machine learning", "data science", "data scientist", "ai engineer",
            "artificial intelligence", "modeling", "classification", "clustering",
            "python", "sql", "pandas",
        }
        if not any(marker in right_clean for marker in ml_markers):
            return 0.0

    target_tokens = expanded_target_tokens(target_role)
    return min(1.0, len(target_tokens & right_tokens) / len(base_tokens))


def cosine_token_score(left, right):
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)

    if not left_tokens or not right_tokens:
        return 0.0

    left_counts = {}
    right_counts = {}

    for token in left_tokens:
        left_counts[token] = left_counts.get(token, 0) + 1

    for token in right_tokens:
        right_counts[token] = right_counts.get(token, 0) + 1

    shared = set(left_counts) & set(right_counts)
    dot = sum(left_counts[token] * right_counts[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (left_norm * right_norm)


def semantic_similarity(left, right, cache_key=None):
    return cosine_token_score(left, right)

def skill_match_score(cv_weighted_skills, job_skills):
    if not isinstance(cv_weighted_skills, dict):
        cv_weighted_skills = {skill: 1.0 for skill in cv_weighted_skills}

    cv_set = set(cv_weighted_skills)
    job_set = set(job_skills)

    if not cv_set or not job_set:
        return 0.0

    matched_skills = cv_set & job_set
    matched_weight = sum(cv_weighted_skills.get(skill, 1.0) for skill in matched_skills)
    required_coverage = min(1.0, matched_weight / len(job_set))
    cv_total_weight = sum(cv_weighted_skills.values()) or 1.0
    cv_relevance = matched_weight / cv_total_weight
    return (0.75 * required_coverage) + (0.25 * cv_relevance)


def requirement_fit_score(cv_weighted_skills, mandatory_skills, nice_to_have_skills, soft_skills=None):
    mandatory = [skill for skill in mandatory_skills or [] if skill not in SOFT_SKILLS]
    nice = [skill for skill in nice_to_have_skills or [] if skill not in SOFT_SKILLS]
    soft = list(soft_skills or [])
    cv_set = set(cv_weighted_skills)

    mandatory_hits = cv_set & set(mandatory)
    nice_hits = cv_set & set(nice)
    soft_hits = cv_set & set(soft)

    if mandatory:
        mandatory_score = sum(cv_weighted_skills.get(skill, 1.0) for skill in mandatory_hits) / len(mandatory)
        mandatory_score = min(1.0, mandatory_score)
    else:
        mandatory_score = 0.6 if nice_hits else 0.0

    nice_score = min(1.0, len(nice_hits) / len(nice)) if nice else 0.0
    soft_score = min(1.0, len(soft_hits) / len(soft)) if soft else 0.0
    total = (0.72 * mandatory_score) + (0.22 * nice_score) + (0.06 * soft_score)

    return {
        "score": max(0.0, min(1.0, total)),
        "mandatoryScore": mandatory_score,
        "niceToHaveScore": nice_score,
        "softScore": soft_score,
        "mandatoryMatched": sorted(mandatory_hits),
        "niceToHaveMatched": sorted(nice_hits),
        "softMatched": sorted(soft_hits),
        "mandatoryMissing": sorted(set(mandatory) - cv_set),
        "niceToHaveMissing": sorted(set(nice) - cv_set),
    }


def generic_job_adjustment(job, matched_skills, cv_role_family, job_family, requirement_fit):
    matched = set(matched_skills or [])
    matched_generic = matched & GENERAL_SUPPORT_SKILLS
    matched_specific = matched - GENERAL_SUPPORT_SKILLS - SOFT_SKILLS
    specificity = float(job.get("jobSpecificity", 0.55))
    generic_ratio = float(job.get("genericSkillRatio", 0.0))
    is_generic_job = bool(job.get("isGenericJob", False))
    specific_cv_family = cv_role_family in SPECIFIC_AUTO_FAMILIES
    family_aligned = role_family_match_score(cv_role_family, job_family) >= 0.65
    requirement_score = float((requirement_fit or {}).get("score", 0.0))
    mandatory_matched = set((requirement_fit or {}).get("mandatoryMatched", []))
    mandatory_specific = mandatory_matched - GENERAL_SUPPORT_SKILLS - SOFT_SKILLS

    penalty = 0.0
    cap = None
    reasons = []

    if not matched:
        return penalty, cap, reasons

    if matched_generic and not matched_specific and cv_role_family not in {"admin", "finance", "general"}:
        penalty += 0.10
        cap = 0.72
        reasons.append("match hanya berasal dari skill pendukung umum")

    if specific_cv_family and family_aligned and is_generic_job and not mandatory_specific:
        penalty += 0.08
        cap = min(cap or 1.0, 0.70)
        reasons.append("lowongan terlalu umum untuk sinyal CV yang lebih spesifik")

    if specificity < 0.45 and generic_ratio >= 0.65 and requirement_score >= 0.70:
        penalty += 0.06
        reasons.append("requirement lowongan didominasi skill umum")

    if cv_role_family in {"admin", "finance"}:
        penalty *= 0.35
        cap = None

    return min(0.22, penalty), cap, reasons[:3]


def specificity_bonus(job, is_auto_mode, cv_role_family, job_family):
    if not is_auto_mode:
        return 0.0
    if cv_role_family not in SPECIFIC_AUTO_FAMILIES:
        return 0.0
    if role_family_match_score(cv_role_family, job_family) < 0.65:
        return 0.0
    specificity = float(job.get("jobSpecificity", 0.55))
    if specificity < 0.70:
        return 0.0
    return min(0.06, (specificity - 0.65) * 0.16)


def core_role_evidence(expected_family, cv_weighted_skills, skill_evidence):
    core_skills = CORE_ROLE_SKILLS.get(expected_family, set())
    if not core_skills:
        return {
            "required": False,
            "score": 1.0,
            "matched": [],
            "strongMatched": [],
            "missing": [],
            "sufficient": True,
        }

    cv_set = set(cv_weighted_skills)
    matched = sorted(cv_set & core_skills)
    strong_labels = {"experience_evidence", "listed_only", "education_evidence"}
    if expected_family in {"design", "culinary", "healthcare", "legal", "security", "sports"}:
        strong_labels = {"experience_evidence", "project_evidence", "education_evidence"}
    weak_labels = {"negative_context", "fuzzy_only"}
    strong_matched = sorted(
        skill for skill in matched
        if skill_evidence.get(skill, {}).get("label") in strong_labels
        or cv_weighted_skills.get(skill, 0) >= 1.1
    )
    weak_only_matched = sorted(
        skill for skill in matched
        if skill_evidence.get(skill, {}).get("label") in weak_labels
    )
    score = min(1.0, (len(matched) * 0.35) + (len(strong_matched) * 0.35))

    if expected_family in STRICT_CORE_FAMILIES:
        # Strict roles need real domain signals. A single project/negative/fuzzy keyword
        # should not overpower a CV whose main evidence is from another family.
        sufficient = (len(matched) >= 2 and len(strong_matched) >= 1 and len(weak_only_matched) < len(matched))
    else:
        supporting_only = expected_family not in {"admin", "finance"} and all(skill in GENERAL_SUPPORT_SKILLS for skill in matched)
        sufficient = bool(matched) and not supporting_only and len(weak_only_matched) < len(matched)

    return {
        "required": True,
        "score": score,
        "matched": matched,
        "strongMatched": strong_matched,
        "weakOnlyMatched": weak_only_matched,
        "missing": sorted(core_skills - cv_set)[:6],
        "sufficient": sufficient,
    }


def has_negative_context(context):
    return any(marker in context for marker in NEGATIVE_CONTEXT_MARKERS)


def extract_cv_skill_evidence(cv_text, cv_weighted_skills, cv_match_types):
    cleaned = clean_text(cv_text)
    evidence = {}
    adjusted = {}

    project_markers = {"project", "projects", "proyek", "portfolio", "portofolio", "github", "aplikasi", "dashboard"}
    experience_markers = {
        "pengalaman", "experience", "work", "intern", "internship", "magang", "kerja",
        "membangun", "mengembangkan", "mengelola", "melakukan", "bertanggung", "collaborated",
    }
    education_markers = {"pendidikan", "education", "universitas", "university", "kuliah", "course", "sertifikasi", "certificate"}
    list_markers = {"skills", "skill", "keahlian", "kemampuan", "technical skills"}

    for skill, weight in cv_weighted_skills.items():
        skill_text = clean_text(skill)
        label = "listed_only"
        multiplier = 0.75
        start = cleaned.find(skill_text)
        context = ""
        if start >= 0:
            context = cleaned[max(0, start - 140): min(len(cleaned), start + len(skill_text) + 140)]

        if context and has_negative_context(context):
            label = "negative_context"
            multiplier = 0.05
        elif cv_match_types.get(skill) == "fuzzy":
            label = "fuzzy_only"
            multiplier = 0.55
        elif any(marker in context for marker in project_markers):
            label = "project_evidence"
            multiplier = 1.35
        elif any(marker in context for marker in experience_markers):
            label = "experience_evidence"
            multiplier = 1.25
        elif any(marker in context for marker in education_markers):
            label = "education_evidence"
            multiplier = 0.95
        elif any(marker in context for marker in list_markers):
            label = "listed_only"
            multiplier = 0.75

        if skill in SOFT_SKILLS:
            multiplier = min(multiplier, 0.65)

        evidence[skill] = {
            "label": label,
            "source": label.replace("_", " "),
            "weight": round(min(MAX_SKILL_WEIGHT, max(0.1, weight * multiplier)), 2),
        }
        adjusted[skill] = evidence[skill]["weight"]

    return adjusted, evidence


def role_match_score(target_role, title, description):
    title_score = target_role_overlap(target_role, title)
    description_score = target_role_overlap(target_role, description[:600])
    if title_score >= 0.75:
        return title_score
    return max(title_score, min(description_score, 0.65))


def get_role_family_terms():
    global ROLE_FAMILY_TERM_CACHE
    if ROLE_FAMILY_TERM_CACHE is None:
        ROLE_FAMILY_TERM_CACHE = tuple(
            (
                family,
                tuple(
                    (term_clean, " " in term_clean)
                    for term_clean in (clean_text(term) for term in terms)
                    if term_clean
                ),
            )
            for family, terms in ROLE_FAMILIES.items()
        )
    return ROLE_FAMILY_TERM_CACHE


def role_family_from_text(text, fallback_domains=None):
    cleaned = clean_text(text)
    fallback_tuple = tuple(fallback_domains or [])
    return role_family_from_cleaned(cleaned, fallback_tuple)


@lru_cache(maxsize=8192)
def role_family_from_cleaned(cleaned, fallback_domains=()):
    cleaned_tokens = set(cleaned.split())
    scores = {}

    for family, terms in get_role_family_terms():
        score = 0.0
        for term_clean, is_phrase in terms:
            term_found = f" {term_clean} " in f" {cleaned} " if is_phrase else term_clean in cleaned_tokens
            if term_found:
                score += 2.0 if term_clean in cleaned[:120] else 1.0
        if score:
            scores[family] = score

    for domain in fallback_domains:
        for family in DOMAIN_TO_ROLE_FAMILY.get(domain, set()):
            scores[family] = scores.get(family, 0.0) + 0.75

    if not scores:
        return "general"

    return max(scores.items(), key=lambda item: item[1])[0]


def role_family_match_score(expected_family, job_family):
    if not expected_family or expected_family == "general":
        return 0.5
    if expected_family == job_family:
        return 1.0
    if (expected_family, job_family) in ROLE_COMPATIBILITY:
        return 0.65
    return 0.10


def infer_cv_role_family(target_role, cv_text, cv_weighted_skills, education_profile, is_auto_mode):
    if not is_auto_mode and target_role:
        return role_family_from_text(target_role)

    skill_text = " ".join(sorted(cv_weighted_skills, key=lambda skill: -cv_weighted_skills[skill])[:12])
    domains = education_profile.get("domains", []) if isinstance(education_profile, dict) else []
    return role_family_from_text(f"{skill_text}. {cv_text[:1200]}", domains)


def infer_job_seniority(title, description):
    text = clean_text(f"{title}. {description[:600]}")
    if any(token in text for token in ("lead", "head", "manager", "supervisor", "senior manager")):
        return "senior_manager"
    if any(token in text for token in ("senior", "sr.", "minimal 5 tahun", "5 tahun", "7 tahun")):
        return "senior"
    if any(token in text for token in ("mid", "middle", "minimal 3 tahun", "3 tahun", "4 tahun")):
        return "mid_level"
    if any(token in text for token in ("junior", "fresh graduate", "entry level", "entry-level")):
        return "junior"
    return "entry_level"


def seniority_match_score(cv_level, job_level, skill_score):
    rank = {
        "entry_level": 0,
        "junior": 1,
        "mid_level": 2,
        "senior": 3,
        "senior_manager": 4,
    }
    cv_rank = rank.get(cv_level, 0)
    job_rank = rank.get(job_level, 0)

    if job_rank <= cv_rank + 1:
        return 1.0
    if skill_score >= 0.85 and job_rank <= cv_rank + 2:
        return 0.75
    return max(0.25, 1.0 - ((job_rank - cv_rank) * 0.25))


def match_confidence(score, risk_flags):
    if risk_flags:
        return "Perlu ditinjau"
    if score >= 75:
        return "Tinggi"
    if score >= 55:
        return "Sedang"
    return "Rendah"


def build_ranking_reasons(matched_skills, role_family_score, corpus_score, education_score, seniority_score, requirement_fit=None):
    reasons = []
    mandatory_hits = (requirement_fit or {}).get("mandatoryMatched", [])
    mandatory_missing = (requirement_fit or {}).get("mandatoryMissing", [])

    if mandatory_hits:
        reasons.append(f"Skill wajib yang terpenuhi: {', '.join(mandatory_hits[:4])}.")
    elif matched_skills:
        reasons.append(f"Skill inti yang cocok: {', '.join(matched_skills[:4])}.")
    if mandatory_missing:
        reasons.append(f"Skill wajib yang belum terlihat: {', '.join(mandatory_missing[:4])}.")
    if role_family_score >= 0.9:
        reasons.append("Role family lowongan selaras dengan target atau sinyal utama CV.")
    elif role_family_score >= 0.6:
        reasons.append("Role family masih berdekatan, tetapi bukan match paling langsung.")
    if corpus_score >= 0.45:
        reasons.append("Kata kunci CV cukup sering muncul pada deskripsi lowongan.")
    if education_score >= 0.7:
        reasons.append("Latar pendidikan/domain CV mendukung lowongan ini.")
    if seniority_score < 0.7:
        reasons.append("Level lowongan tampak lebih tinggi dari pengalaman CV.")
    return reasons or ["Kecocokan dihitung dari overlap skill wajib, role, domain, dan konteks lowongan."]


def transferable_score(cv_skills, job_text):
    if not cv_skills:
        return 0.0

    return overlap_score(" ".join(cv_skills), job_text)


def education_match_score(education_profile, job_domains):
    cv_domains = set(education_profile.get("domains", []))
    job_domain_set = set(job_domains or [])
    cv_degrees = set(education_profile.get("degrees", []))

    if not cv_domains or not job_domain_set:
        return 0.5

    if "culinary" in job_domain_set and "culinary" not in cv_domains:
        return 0.25

    # K9: Strict check for highly-specific domains
    for strict_domain in ("healthcare", "legal"):
        if strict_domain in job_domain_set and strict_domain not in cv_domains:
            return 0.20

    if cv_domains & job_domain_set:
        base_score = 1.0
        # K9: Adjust based on degree level
        high_degrees = {"s2", "s3", "master", "magister"}
        low_degrees = {"sma", "smk", "d1", "d2"}
        if cv_degrees & high_degrees:
            base_score = min(1.0, base_score + 0.05)
        elif cv_degrees & low_degrees:
            base_score = max(0.6, base_score - 0.15)
        return round(base_score, 2)

    compatible_pairs = {
        ("it", "data_ai"),
        ("data_ai", "it"),
        ("business", "finance"),
        ("finance", "business"),
        ("design", "it"),
        ("logistics", "engineering"),
        ("engineering", "logistics"),
        ("business", "logistics"),
    }

    if any(
        (cv_domain, job_domain) in compatible_pairs
        for cv_domain in cv_domains
        for job_domain in job_domain_set
    ):
        return 0.7

    return 0.25


def calculate_final_score(
    skill_score,
    semantic_score,
    role_score,
    transfer_score,
    education_score,
    missing_ratio,
    is_auto_mode=False,
    role_family_score=0.5,
    seniority_score=1.0,
    corpus_score=None,
    requirement_score=None,
):
    """
    Weighted hybrid scoring formula.

    Targeted mode weights (rationale):
      40% Skill Match     â€” primary signal; technical overlap is most reliable
      20% Role Match      â€” ensures job title relevance to user's target
      15% Semantic        â€” context similarity; conservative weight (small model)
      15% Education Match â€” domain alignment provides meaningful signal
      10% Transferable    â€” broad token overlap as weaker supporting signal

    Auto mode (no target role) â€” role_score removed; semantic gets higher weight:
      45% Skill Match
      25% Semantic
      15% Transferable
      15% Education Match

    Missing skill penalty: capped at 20% to avoid over-penalising partial CVs.
    Role cap: if role_score < 0.05 the job is likely irrelevant; clamp to 0.35.
    """
    corpus_value = semantic_score if corpus_score is None else corpus_score
    requirement_value = skill_score if requirement_score is None else requirement_score

    if is_auto_mode:
        raw_score = (
            (0.24 * skill_score)
            + (0.20 * requirement_value)
            + (0.22 * role_family_score)
            + (0.15 * corpus_value)
            + (0.10 * transfer_score)
            + (0.06 * education_score)
            + (0.05 * seniority_score)
        )
        penalty = min(0.20, missing_ratio * 0.15)
        return max(0.0, min(1.0, raw_score - penalty))

    raw_score = (
        (0.22 * skill_score)
        + (0.18 * requirement_value)
        + (0.21 * role_score)
        + (0.24 * role_family_score)
        + (0.10 * corpus_value)
        + (0.04 * transfer_score)
        + (0.06 * education_score)
        + (0.05 * seniority_score)
    )
    penalty = min(0.20, missing_ratio * 0.20)
    final_score = max(0.0, min(1.0, raw_score - penalty))
    if role_score < 0.05:
        final_score = min(final_score, 0.35)
    if role_family_score < 0.25:
        final_score = min(final_score, 0.45 if skill_score >= 0.7 else 0.35)
    if requirement_value < 0.20:
        final_score = min(final_score, 0.42 if role_family_score >= 0.65 else 0.30)
    if seniority_score < 0.55:
        final_score = min(final_score, 0.55)
    if education_score < 0.30 and role_family_score < 0.65:
        final_score = min(final_score, 0.40)
    return final_score


def format_education_label(education_profile):
    majors = education_profile.get("majors", [])
    domains = education_profile.get("domains", [])

    if majors:
        return ", ".join(major.title() for major in majors[:3])

    if domains:
        return ", ".join(domain.replace("_", " ").upper() for domain in domains[:3])

    return "belum terdeteksi jelas"


def format_list(items, limit=4, empty_text="belum terdeteksi"):
    values = [str(item) for item in (items or []) if item]
    if not values:
        return empty_text
    if len(values) <= limit:
        return ", ".join(values)
    return f"{', '.join(values[:limit])}, dan {len(values) - limit} lainnya"


def target_skill_candidates(target_family, target_core_evidence=None, limit=5):
    skills = list(target_core_evidence.get("missing", [])) if target_core_evidence else []
    if not skills:
        skills = list((ROADMAP_TEMPLATES.get(target_family) or {}).get("skills", []))
    if not skills:
        skills = [
            term for term in sorted(ROLE_FAMILIES.get(target_family, []))
            if len(term) > 2 and term not in {"food", "data", "office", "sport"}
        ]
    return skills[:limit]


def role_action_example(target_family):
    return ROLE_ACTION_EXAMPLES.get(
        target_family,
        "Contoh: tulis tugas utama, alat/prosedur yang dipakai, dan hasil yang terlihat dari pekerjaan tersebut.",
    )


def skill_relevant_to_family(skill, target_family):
    if not target_family or target_family == "general":
        return True

    skill_text = clean_text(skill)
    if not skill_text:
        return False

    terms = set(ROLE_FAMILIES.get(target_family, set()))
    terms.update((ROADMAP_TEMPLATES.get(target_family) or {}).get("skills", []))
    terms.update(CORE_ROLE_SKILLS.get(target_family, set()))

    for term in terms:
        term_text = clean_text(term)
        if not term_text:
            continue
        if skill_text == term_text or skill_text in term_text or term_text in skill_text:
            return True

    family_aliases = {
        "data": {"database", "visualization", "analytics", "analysis"},
        "backend": {"database", "api", "server", "programming"},
        "frontend": {"ui", "web", "programming"},
        "fullstack": {"database", "api", "web", "programming"},
        "admin": {"administration", "administrative", "document", "office"},
        "logistics": {"warehouse", "stock", "inventory", "shipping", "delivery"},
        "hospitality": {"guest", "service", "reservation", "hotel"},
        "education": {"teaching", "teacher", "lesson", "classroom", "training"},
        "culinary": {"cook", "food", "kitchen", "chef", "hygiene"},
    }
    return any(alias in skill_text for alias in family_aliases.get(target_family, set()))


def course_relevant_to_family(skill, target_family):
    if not skill:
        return False
    if not target_family or target_family == "general":
        return True

    skill_text = clean_text(skill)
    allowed = COURSE_RECOMMENDATION_SKILL_ALLOWLIST.get(target_family, set())
    if skill_text in allowed:
        return True

    return skill_relevant_to_family(skill_text, target_family)


def build_summary(target_role, detected_skills, missing_skills, score, education_profile=None, weighted_skills=None):
    skill_text = format_list(detected_skills, 6, "belum ada skill yang terbaca jelas")
    missing_text = format_list(missing_skills, 4, "belum ada gap skill utama")
    education_text = format_education_label(education_profile or {})

    # K11: Mention top skills by confidence weight
    confidence_note = ""
    if weighted_skills:
        top_confident = sorted(weighted_skills.items(), key=lambda x: -x[1])[:3]
        top_names = ", ".join(sk for sk, _ in top_confident)
        confidence_note = f" Sinyal terkuat dari CV saat ini adalah {top_names}."

    if score >= 75:
        verdict = "CV sudah berada di jalur yang sangat dekat dengan target"
    elif score >= 60:
        verdict = "CV sudah cukup kuat, tetapi masih bisa dibuat lebih meyakinkan"
    elif score >= 40:
        verdict = "CV mulai menunjukkan arah yang relevan, namun buktinya masih perlu dipertegas"
    elif score > 0:
        verdict = "CV belum cukup kuat untuk target ini dan perlu penyesuaian yang lebih terarah"
    else:
        verdict = "CV belum menghasilkan kecocokan yang aman untuk direkomendasikan"

    return (
        f"Untuk target {target_role}, {verdict}. "
        f"Latar pendidikan yang terbaca: {education_text}. Skill yang paling terlihat: {skill_text}."
        f"{confidence_note} Prioritas perbaikan utama: {missing_text}."
    )


def build_improvements(detected_skills, missing_skills, weighted_skills=None, target_role="", target_family="general"):
    """K12: Generate specific, personalised improvement tips based on actual gaps."""
    improvements = []

    if not detected_skills:
        improvements.append(
            "Gunakan PDF berbasis teks, bukan scan gambar, agar sistem bisa membaca skill dan pengalaman dengan akurat."
        )
        return improvements

    # K11+K12: Skills detected but with low confidence â€” suggest strengthening context
    if weighted_skills:
        soft_skill_names = {
            "time management", "problem solving", "teamwork", "collaboration",
            "leadership", "communication", "interpersonal", "effective communication",
        }
        low_confidence = [
            sk for sk, wt in weighted_skills.items()
            if wt < 1.2 and sk not in soft_skill_names
        ]
        relevant_low_confidence = [
            skill for skill in low_confidence
            if skill_relevant_to_family(skill, target_family)
        ]
        if relevant_low_confidence:
            improvements.append(
                f"Perkuat bukti untuk {format_list(relevant_low_confidence, 4)}. "
                "Jangan hanya ditulis di daftar skill; masukkan ke pengalaman, project, atau pencapaian agar terlihat pernah dipakai."
            )
        elif target_family and target_family != "general":
            target_skills = target_skill_candidates(target_family)
            improvements.append(
                f"Tonjolkan bukti yang paling dekat dengan target {target_role or 'pekerjaan ini'}, "
                f"terutama {format_list(target_skills, 4, 'skill inti target')}. "
                "Kurangi penekanan pada skill yang tidak langsung mendukung target tersebut."
            )

    # K12: Specific missing skills mapped to safe, role-aware local courses.
    if missing_skills:
        from modules.nlp import SAFE_RECOMMENDATION_DATABASE
        specific_tips = []
        for skill in missing_skills:
            skill_lower = skill.lower()
            if skill_lower in SAFE_RECOMMENDATION_DATABASE and course_relevant_to_family(skill_lower, target_family):
                entry = SAFE_RECOMMENDATION_DATABASE[skill_lower]
                specific_tips.append(f"{skill.title()} ({entry['course']})")
        
        if specific_tips:
            improvements.append(
                f"Prioritaskan penguasaan skill berikut: {', '.join(specific_tips)}. "
                "Fokuslah menyelesaikan salah satu kursus di atas untuk menutup kesenjangan keahlian Anda."
            )
        else:
            improvements.append(
                f"Prioritaskan gap yang paling berpengaruh: {format_list(missing_skills, 4)}. "
                "Pilih 1-2 skill dulu, lalu tunjukkan lewat project kecil atau pengalaman yang konkret."
            )

    improvements.append(
        "Ubah deskripsi pengalaman menjadi pola tindakan dan dampak: apa yang dikerjakan, tools yang dipakai, dan hasilnya. "
        f"{role_action_example(target_family)}"
    )
    target_label = target_role or "target pekerjaan"
    improvements.append(f"Sesuaikan headline atau ringkasan profil dengan target {target_label} agar recruiter langsung menangkap arah karier Anda.")

    return improvements


def build_target_mismatch_improvements(target_role, target_family, detected_skills, target_core_evidence=None, suggested_target_roles=None):
    """Generate target-aware tips when the CV is not yet credible for the requested role."""
    target_skills = target_skill_candidates(target_family, target_core_evidence)
    visible_strengths = format_list(detected_skills, 4, "skill dari CV saat ini")
    target_skill_text = format_list(target_skills, 4, "skill inti target")
    target_label = target_role or "target pekerjaan ini"
    suggestions = [role for role in (suggested_target_roles or []) if role][:3]

    improvements = [
        (
            f"CV saat ini lebih kuat di area {visible_strengths}, sedangkan target {target_label} "
            f"membutuhkan bukti yang lebih langsung seperti {target_skill_text}."
        ),
        (
            f"Tambahkan pengalaman, project, pelatihan, atau sertifikasi yang benar-benar relevan dengan {target_label}. "
            "Tuliskan aktivitas, alat/prosedur yang dipakai, dan hasil yang bisa diverifikasi."
        ),
        (
            f"Ubah headline dan ringkasan profil agar jujur mengarah ke {target_label}; jangan hanya mengganti kata kunci "
            "jika pengalaman pendukungnya belum ada."
        ),
    ]

    if suggestions:
        improvements.append(
            f"Jika ingin hasil yang lebih realistis dari CV saat ini, coba target alternatif: {format_list(suggestions, 3)}."
        )
    else:
        improvements.append("Gunakan mode otomatis untuk melihat target pekerjaan yang paling dekat dengan isi CV saat ini.")

    return improvements


def build_match_reason(title, matched_skills, role_score, semantic_score, education_score=None):
    reasons = []

    if matched_skills:
        reasons.append(f"Lowongan {title} relevan karena CV sudah menunjukkan skill seperti {format_list(matched_skills, 5)}.")

    if role_score >= 0.55:
        reasons.append("Judul atau kebutuhan lowongan cukup dekat dengan target yang dipilih.")
    elif role_score >= 0.25:
        reasons.append("Ada irisan antara target pekerjaan dan kebutuhan lowongan, meskipun belum sepenuhnya spesifik.")

    if semantic_score >= 0.55:
        reasons.append("Kata kunci dan konteks CV juga cukup sering muncul di deskripsi lowongan.")

    if education_score is not None:
        if education_score >= 0.9:
            reasons.append("Latar pendidikan yang terbaca mendukung domain pekerjaan ini.")
        elif education_score >= 0.65:
            reasons.append("Latar pendidikan masih cukup dekat dengan domain pekerjaan.")

    if not reasons:
        reasons.append("Kecocokan masih rendah karena bukti di CV belum cukup kuat untuk dikaitkan dengan lowongan ini.")

    return " ".join(reasons)


def build_gap_reason(title, matched_skills, missing_skills, role_score, semantic_score, education_score=None):
    reasons = []

    if missing_skills:
        reasons.append(
            f"Untuk mengejar lowongan {title}, bukti yang paling perlu ditambahkan adalah {format_list(missing_skills, 6)}."
        )
    elif matched_skills:
        reasons.append(
            f"Skill {format_list(matched_skills, 3)} sudah terlihat; berikutnya jelaskan konteks pemakaiannya agar lebih meyakinkan untuk {title}."
        )

    if role_score < 0.25:
        reasons.append("Judul lowongan belum terlalu dekat dengan target, jadi CV perlu sinyal role yang lebih eksplisit.")
    elif role_score < 0.55:
        reasons.append("Perkuat headline atau ringkasan CV agar keyword target lebih mudah terbaca.")

    if semantic_score < 0.25:
        reasons.append("Konteks pengalaman di CV masih belum banyak menyerupai requirement lowongan.")
    elif semantic_score < 0.55:
        reasons.append("Gunakan istilah yang lebih dekat dengan requirement lowongan, tetapi tetap berdasarkan pengalaman nyata.")

    if education_score is not None and education_score < 0.4:
        reasons.append("Hubungan antara pendidikan dan domain pekerjaan belum terlihat jelas.")
    elif education_score is not None and education_score < 0.7:
        reasons.append("Jika relevan, jelaskan bagaimana pendidikan atau tugas kuliah mendukung pekerjaan ini.")

    if not reasons:
        reasons.append(
            f"Kecocokan untuk {title} sudah cukup baik. Perkuat dengan contoh project, pencapaian, atau metrik dampak agar tidak terlihat generik."
        )

    return " ".join(reasons)


def build_job_improvements(title, matched_skills, missing_skills, role_score, semantic_score, education_score=None):
    improvements = []

    if missing_skills:
        improvements.append(
            f"Buat atau tonjolkan bukti untuk {format_list(missing_skills, 5)} melalui project, tugas kuliah, sertifikasi, atau pengalaman kerja."
        )
    elif matched_skills:
        improvements.append(
            f"Perjelas cara Anda memakai {format_list(matched_skills, 3)}: masalah yang diselesaikan, tools yang dipakai, dan hasil akhirnya."
        )

    if role_score < 0.25:
        improvements.append(
            "Ubah headline atau ringkasan profil agar lebih langsung menyebut target role dan skill inti yang diminta lowongan."
        )
    elif role_score < 0.55:
        improvements.append(
            "Tambahkan 1 kalimat ringkasan yang menghubungkan pengalaman Anda dengan kebutuhan utama lowongan."
        )

    if semantic_score < 0.25:
        improvements.append(
            "Samakan istilah di CV dengan requirement lowongan, selama memang sesuai dengan pengalaman yang Anda punya."
        )
    elif semantic_score < 0.55:
        improvements.append(
            "Tambahkan detail konteks: jenis aplikasi/proses yang dikerjakan, ukuran tugas, dan hasil yang dicapai."
        )

    if education_score is not None and education_score < 0.4:
        improvements.append(
            "Jelaskan hubungan pendidikan, tugas akhir, project kampus, atau pelatihan dengan domain pekerjaan ini."
        )
    elif education_score is not None and education_score < 0.7:
        improvements.append(
            "Pertegas bagian pendidikan yang mendukung lowongan, misalnya mata kuliah, project, atau sertifikasi terkait."
        )

    if not improvements:
        improvements.append(
            "CV sudah cukup relevan; langkah berikutnya adalah menambahkan metrik, link portofolio, atau contoh hasil kerja agar posisinya lebih kuat."
        )

    return improvements


def target_available_score(target_role, jobs, target_family):
    if not target_role:
        return True, "Mode otomatis memilih target dari sinyal CV dan dataset lowongan.", 1.0

    if target_family == "general":
        return (
            False,
            f"Target {target_role} belum dikenali dalam taxonomy role JobFit.",
            0.0,
        )

    target_clean = clean_text(target_role)
    football_target = target_family == "sports" and any(
        token in target_clean
        for token in ("bola", "sepak", "soccer", "football", "futsal", "pemain")
    )
    football_terms = {"bola", "sepak", "soccer", "football", "futsal", "player", "pemain", "athlete", "atlet"}
    best_score = 0.0
    best_title = ""
    for job in jobs:
        title = job.get("title", "")
        keyword = job.get("keyword", "")
        title_keyword_tokens = token_set(f"{title}. {keyword}")
        job_family = job.get("jobFamily") or role_family_from_text(
            f"{title}. {keyword}.",
            job.get("jobDomains", []),
        )
        title_overlap = target_role_overlap(target_role, title)
        keyword_overlap = target_role_overlap(target_role, keyword)
        family_score = role_family_match_score(target_family, job_family)
        if football_target and not (title_keyword_tokens & football_terms):
            family_score = 0.0
            title_overlap = 0.0
            keyword_overlap = 0.0
        availability = max(title_overlap, keyword_overlap, family_score)
        if availability > best_score:
            best_score = availability
            best_title = title

    if best_score >= 0.65:
        return True, f"Target tersedia di dataset, contoh lowongan terdekat: {best_title}.", best_score

    return (
        False,
        f"Target {target_role} belum tersedia di dataset lowongan JobFit saat ini.",
        best_score,
    )


def suggest_target_roles(cv_role_family, detected_skills, jobs, limit=5):
    skill_set = set(detected_skills or [])
    primary_suggestions = []
    fallback_suggestions = []
    seen_titles = set()

    for job in jobs:
        title = job.get("title", "")
        if not title:
            continue
        normalized_title = clean_text(title)
        if normalized_title in seen_titles:
            continue

        job_family = job.get("jobFamily") or role_family_from_text(
            f"{title}. {job.get('keyword', '')}.",
            job.get("jobDomains", []),
        )
        family_score = role_family_match_score(cv_role_family, job_family)
        mandatory_hits = len(skill_set & set(job.get("mandatorySkills", [])))
        nice_hits = len(skill_set & set(job.get("niceToHaveSkills", [])))
        mandatory_total = len(job.get("mandatorySkills", [])) or 1
        mandatory_coverage = min(1.0, mandatory_hits / mandatory_total)
        corpus_score = jobs_service.corpus_relevance_score(" ".join(detected_skills[:12]), job)
        score = (0.48 * family_score) + (0.34 * mandatory_coverage) + (0.10 * min(1.0, nice_hits / 4)) + (0.08 * corpus_score)

        if score < 0.35:
            continue

        item = (score, title.title(), job_family)
        if cv_role_family != "general" and family_score >= 0.65:
            primary_suggestions.append(item)
        else:
            fallback_suggestions.append(item)
        seen_titles.add(normalized_title)

    primary_suggestions.sort(key=lambda item: item[0], reverse=True)
    fallback_suggestions.sort(key=lambda item: item[0], reverse=True)
    suggestions = primary_suggestions + fallback_suggestions
    return [title for _, title, _ in suggestions[:limit]]


def build_suggestion_reason(cv_role_family, suggested_target_roles):
    if not suggested_target_roles:
        return "Belum ada target alternatif yang cukup kuat dari dataset saat ini. Coba pilih target yang lebih umum atau unggah CV dengan bukti pengalaman yang lebih lengkap."
    return (
        f"Saran target ini dipilih karena paling dekat dengan sinyal CV di area {cv_role_family}, "
        "terutama dari skill wajib lowongan dan keyword yang tersedia di dataset."
    )


def build_evidence_summary(skill_evidence):
    counts = Counter(item.get("label", "unknown") for item in skill_evidence.values())
    return {
        "projectEvidence": counts.get("project_evidence", 0),
        "experienceEvidence": counts.get("experience_evidence", 0),
        "educationEvidence": counts.get("education_evidence", 0),
        "listedOnly": counts.get("listed_only", 0),
        "fuzzyOnly": counts.get("fuzzy_only", 0),
        "negativeContext": counts.get("negative_context", 0),
    }


def build_career_roadmap(role_family, missing_skills, detected_skills, cv_experience_level):
    template = ROADMAP_TEMPLATES.get(role_family) or ROADMAP_TEMPLATES.get("admin", {})
    template_skills = template.get("skills", [])
    detected = set(detected_skills or [])
    priority_skills = []

    for skill in list(missing_skills or []) + template_skills:
        if skill not in detected and skill not in priority_skills:
            priority_skills.append(skill)

    first_skills = priority_skills[:3] or template_skills[:3]
    level_note = "mulai dari project kecil yang bisa selesai dan dipamerkan" if cv_experience_level in {"entry_level", "junior"} else "tambahkan bukti impact yang lebih terukur"
    steps = [
        f"Perjelas arah CV ke jalur {role_family.replace('_', ' ')} dengan headline singkat dan 2-3 skill inti yang benar-benar terbukti.",
        f"Fokuskan pembelajaran berikutnya pada {format_list(first_skills, 3)} karena gap ini paling berpengaruh ke rekomendasi.",
        f"Buat portofolio terarah: {level_note}, lalu tulis tools, peran Anda, dan hasil akhirnya.",
        "Ubah pengalaman atau project menjadi cerita singkat: masalah, tindakan, tools, dan dampak yang bisa diukur.",
    ]

    # K12: Pull safe, role-aware project ideas for missing skills.
    from modules.nlp import SAFE_RECOMMENDATION_DATABASE
    custom_projects = []
    for skill in priority_skills:
        skill_lower = skill.lower()
        if skill_lower in SAFE_RECOMMENDATION_DATABASE and course_relevant_to_family(skill_lower, role_family):
            proj = SAFE_RECOMMENDATION_DATABASE[skill_lower]["project"]
            if proj not in custom_projects:
                custom_projects.append(proj)

    # Use custom projects if found, otherwise fall back to template projects
    final_projects = custom_projects[:3]
    if len(final_projects) < 3:
        template_projects = template.get("projects", [])
        for p in template_projects:
            if p not in final_projects:
                final_projects.append(p)
            if len(final_projects) >= 3:
                break

    return steps, final_projects[:3]


def audit_cv_quality(cv_text, detected_skills, work_experiences, target_role, target_available):
    text = clean_text(cv_text)
    findings = []
    hints = []
    score = 100

    if len(text) < 900:
        score -= 15
        findings.append("Isi CV yang terbaca masih terlalu singkat, sehingga sistem belum punya cukup bukti untuk menilai kekuatan kandidat.")
        hints.append("Tambahkan ringkasan profil, 2-3 pengalaman/project, daftar skill teknis, dan pencapaian yang bisa diverifikasi.")

    if not work_experiences:
        score -= 15
        findings.append("Bagian pengalaman atau project belum terbaca secara terstruktur.")
        hints.append("Tulis pengalaman dengan format: posisi/project, organisasi/perusahaan, durasi, kontribusi, dan hasil.")

    if not any(char.isdigit() for char in cv_text):
        score -= 10
        findings.append("CV belum menunjukkan angka pencapaian atau ukuran dampak.")
        hints.append("Tambahkan metrik seperti jumlah user, jumlah data, persentase peningkatan, durasi project, atau target yang dicapai.")

    if len(detected_skills or []) < 5:
        score -= 15
        findings.append("Skill yang terbaca masih sedikit atau terlalu umum untuk membuat rekomendasi yang kuat.")
        hints.append("Cantumkan skill inti di dalam pengalaman/project, bukan hanya di daftar skill.")

    if "project" not in text and "proyek" not in text and "portfolio" not in text and "portofolio" not in text:
        score -= 10
        findings.append("Bagian project atau portofolio belum terlihat jelas.")
        hints.append("Tambahkan 2-3 project paling relevan, lengkap dengan tujuan, tools, fitur, dan hasil.")

    if target_role and target_role.lower() not in cv_text.lower():
        score -= 8
        findings.append("Target pekerjaan belum terlihat eksplisit di headline atau ringkasan CV.")
        hints.append("Tambahkan headline yang langsung menyebut target role, misalnya 'Frontend Developer' atau 'Data Analyst'.")

    if target_available is False:
        score -= 7
        findings.append("Target yang dipilih belum tersedia di dataset lowongan, sehingga JobFit tidak memaksakan rekomendasi palsu.")
        hints.append("Gunakan target alternatif yang disarankan karena target tersebut lebih dekat dengan isi CV dan dataset lowongan.")

    if not findings:
        findings.append("Struktur CV sudah cukup terbaca dan memiliki bukti skill yang bisa dipakai untuk matching.")
        hints.append("Perkuat lagi dengan angka dampak, link portofolio, dan project paling relevan agar ranking makin kompetitif.")

    return max(0, min(100, score)), findings[:5], hints[:5]


def build_job_evidence(matched_skills, missing_skills, cv_match_types, role_family_score, corpus_score, requirement_fit=None, skill_evidence=None):
    strong = []
    weak = []
    requirement_fit = requirement_fit or {}
    skill_evidence = skill_evidence or {}

    for skill in matched_skills:
        match_type = cv_match_types.get(skill, "exact")
        evidence_label = skill_evidence.get(skill, {}).get("label", "")
        if skill in requirement_fit.get("mandatoryMatched", []):
            strong.append(f"{skill} (wajib)")
        elif match_type == "exact" and skill not in SOFT_SKILLS and evidence_label in {"project_evidence", "experience_evidence"}:
            strong.append(skill)
        else:
            weak.append(skill)

    if role_family_score >= 0.9:
        strong.append("role family cocok")
    elif role_family_score >= 0.6:
        weak.append("role family berdekatan")

    if corpus_score >= 0.55:
        strong.append("konteks CV mirip requirement")
    elif corpus_score >= 0.35:
        weak.append("sebagian keyword requirement cocok")

    missing_priority = list(requirement_fit.get("mandatoryMissing", [])) + list(requirement_fit.get("niceToHaveMissing", [])) + list(missing_skills)
    seen = set()
    missing_clean = []
    for skill in missing_priority:
        if skill not in seen:
            missing_clean.append(skill)
            seen.add(skill)

    return strong[:8], weak[:8], missing_clean[:8]


def is_display_eligible(is_auto_mode, target_available, role_family_score, skill_score, corpus_score, role_score, strong_evidence, requirement_fit=None):
    if not is_auto_mode and target_available is False:
        return False

    requirement_score = (requirement_fit or {}).get("score", skill_score)
    mandatory_score = (requirement_fit or {}).get("mandatoryScore", 0.0)
    has_core_evidence = bool(strong_evidence) and (
        requirement_score >= 0.20 or skill_score >= 0.22 or corpus_score >= 0.45 or role_score >= 0.50
    )

    if role_family_score >= 0.65 and has_core_evidence and (mandatory_score >= 0.15 or corpus_score >= 0.30 or requirement_score >= 0.20):
        return True

    if is_auto_mode and requirement_score >= 0.40 and skill_score >= 0.40 and corpus_score >= 0.40:
        return True

    return False


def token_overlap_ratio(left_tokens, right_tokens):
    if not left_tokens or not right_tokens:
        return 0.0

    return len(left_tokens & right_tokens) / len(left_tokens)


def fast_target_overlap_score(target_role, target_tokens, job):
    if not target_tokens:
        return 0.0

    expanded_tokens = expanded_target_tokens(target_role)
    title_keyword_tokens = set(job.get("titleTokens", set())) | set(job.get("keywordTokens", set()))
    description_tokens = set(job.get("descriptionTokens", set()))
    title_keyword_score = len(expanded_tokens & title_keyword_tokens) / len(target_tokens)
    description_score = len(expanded_tokens & description_tokens) / len(target_tokens)
    return min(1.0, max(title_keyword_score, description_score))


def candidate_prefilter_score(job, cv_weighted_skills, target_role, cv_tokens, target_tokens, education_profile, is_auto_mode, cv_role_family):
    job_skills = job["jobSkillSet"]
    skill_score = skill_match_score(cv_weighted_skills, job["jobSkills"])
    matched_weight = sum(cv_weighted_skills.get(skill, 1.0) for skill in set(cv_weighted_skills) & job_skills)
    cv_total_weight = sum(cv_weighted_skills.values()) or 1.0
    cv_overlap = matched_weight / cv_total_weight
    transfer_score = token_overlap_ratio(cv_tokens, job["descriptionTokens"])
    education_score = education_match_score(education_profile, job["jobDomains"])
    role_score = 0.0 if is_auto_mode else role_match_score(target_role, job["title"], job["description"])
    job_family = job.get("jobFamily") or role_family_from_text(f"{job['title']}. {job.get('keyword', '')}.", job.get("jobDomains", []))
    family_score = role_family_match_score(cv_role_family, job_family)
    corpus_score = jobs_service.corpus_relevance_score(f"{target_role}. {' '.join(cv_weighted_skills)}", job)
    specificity = float(job.get("jobSpecificity", 0.55))
    generic_penalty = 0.07 if is_auto_mode and cv_role_family in SPECIFIC_AUTO_FAMILIES and job.get("isGenericJob") else 0.0
    specificity_lift = min(0.05, max(0.0, specificity - 0.65) * 0.12) if is_auto_mode and family_score >= 0.65 else 0.0

    return max(0.0, (
        (0.30 * skill_score)
        + (0.20 * family_score)
        + (0.18 * cv_overlap)
        + (0.14 * corpus_score)
        + (0.10 * role_score)
        + (0.08 * education_score)
        + (0.05 * transfer_score)
        + specificity_lift
        - generic_penalty
    ))


def lightweight_candidate_score(job, cv_weighted_skills, target_role, cv_tokens, education_profile, is_auto_mode, cv_role_family):
    job_skills = job["jobSkillSet"]
    matched_weight = sum(cv_weighted_skills.get(skill, 1.0) for skill in set(cv_weighted_skills) & job_skills)
    cv_total_weight = sum(cv_weighted_skills.values()) or 1.0
    cv_overlap = matched_weight / cv_total_weight
    skill_score = skill_match_score(cv_weighted_skills, job["jobSkills"])
    transfer_score = token_overlap_ratio(cv_tokens, job["requirementTokens"])
    education_score = education_match_score(education_profile, job["jobDomains"])
    role_score = 0.0 if is_auto_mode else role_match_score(target_role, job["title"], job["description"])
    job_family = job.get("jobFamily") or role_family_from_text(f"{job['title']}. {job.get('keyword', '')}.", job.get("jobDomains", []))
    family_score = role_family_match_score(cv_role_family, job_family)
    specificity = float(job.get("jobSpecificity", 0.55))
    generic_penalty = 0.06 if is_auto_mode and cv_role_family in SPECIFIC_AUTO_FAMILIES and job.get("isGenericJob") else 0.0
    specificity_lift = min(0.04, max(0.0, specificity - 0.65) * 0.10) if is_auto_mode and family_score >= 0.65 else 0.0

    return max(0.0, (
        (0.34 * skill_score)
        + (0.24 * family_score)
        + (0.18 * cv_overlap)
        + (0.12 * role_score)
        + (0.07 * education_score)
        + (0.05 * transfer_score)
        + specificity_lift
        - generic_penalty
    ))


def select_candidate_jobs(jobs, cv_weighted_skills, target_role, cv_text, education_profile, is_auto_mode, cv_role_family):
    cv_tokens = token_set(cv_text[:2500])
    target_tokens = token_set(target_role)
    candidate_pool = jobs
    candidate_limit = AUTO_MAX_CANDIDATE_JOBS if is_auto_mode else MAX_CANDIDATE_JOBS

    if not is_auto_mode:
        role_matched_jobs = [
            job for job in jobs
            if fast_target_overlap_score(target_role, target_tokens, job) >= 0.25
            or role_family_match_score(
                cv_role_family,
                job.get("jobFamily") or role_family_from_text(f"{job['title']}. {job.get('keyword', '')}.", job.get("jobDomains", [])),
            ) >= 0.65
        ]
        if role_matched_jobs:
            candidate_pool = role_matched_jobs
    else:
        family_matched_jobs = [
            job for job in jobs
            if role_family_match_score(
                cv_role_family, job.get("jobFamily")
            ) >= 0.65
        ]
        if family_matched_jobs:
            candidate_pool = family_matched_jobs

    lightweight_limit = max(candidate_limit * (2 if is_auto_mode else 3), 220 if is_auto_mode else 300)
    if len(candidate_pool) > lightweight_limit:
        candidate_pool = sorted(
            candidate_pool,
            key=lambda job: lightweight_candidate_score(
                job,
                cv_weighted_skills,
                target_role,
                cv_tokens,
                education_profile,
                is_auto_mode,
                cv_role_family,
            ),
            reverse=True,
        )[:lightweight_limit]

    ranked_jobs = sorted(
        candidate_pool,
        key=lambda job: candidate_prefilter_score(
            job,
            cv_weighted_skills,
            target_role,
            cv_tokens,
            target_tokens,
            education_profile,
            is_auto_mode,
            cv_role_family,
        ),
        reverse=True,
    )

    return ranked_jobs[: min(candidate_limit, len(ranked_jobs))]


ANALYSIS_CACHE = {}
MAX_ANALYSIS_CACHE_ITEMS = 50


def get_file_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def analysis_cache_signature():
    jobs_signature = jobs_service.get_jobs_cache_signature()
    return json.dumps(
        {
            "jobs": jobs_signature,
            "nlp": NLP_CACHE_VERSION,
            "scoring": SCORING_CACHE_VERSION,
        },
        sort_keys=True,
        default=str,
    )


def new_analysis_id():
    return f"analysis-{uuid.uuid4().hex}"


def clone_cached_analysis(payload):
    cached = copy.deepcopy(payload)
    cached["id"] = new_analysis_id()
    cached["date"] = time.strftime("%d %B %Y")
    return cached


def analyze_cv_file(pdf_path, target_role, analysis_mode="targeted"):
    total_started = time.perf_counter()
    stage_timings = {}
    try:
        pdf_hash = get_file_md5(pdf_path)
    except Exception:
        pdf_hash = None

    normalized_target = clean_text(target_role or "")
    signature = analysis_cache_signature()
    cache_key = (pdf_hash, normalized_target, analysis_mode, signature)
    if pdf_hash and cache_key in ANALYSIS_CACHE:
        logger.info("Found CV analysis in memory cache.")
        return clone_cached_analysis(ANALYSIS_CACHE[cache_key])

    stage_started = time.perf_counter()
    jobs = jobs_service.prepare_jobs_once()
    log_analysis_stage(stage_timings, "prepare_jobs", stage_started)

    stage_started = time.perf_counter()
    cv_text = extract_text_from_pdf(pdf_path)
    cv_text_length = len(cv_text.strip())
    log_analysis_stage(stage_timings, "extract_text", stage_started)

    stage_started = time.perf_counter()
    # --- GEMINI API INTEGRATION & FALLBACK ---
    gemini_profile = extract_profile_with_gemini(cv_text, target_role=target_role)
    gemini_summary = ""
    gemini_improvements = []
    
    if gemini_profile:
        # Reconstruct skills
        gemini_skills_text = ", ".join(gemini_profile.get("skills", []))
        cv_weighted_skills, cv_match_types = extract_weighted_skills(gemini_skills_text)
        
        # Use local parsing if no skills found, otherwise keep Gemini skills
        if not cv_weighted_skills:
            cv_weighted_skills, cv_match_types = extract_weighted_skills(cv_text)
            
        # Reconstruct education
        gemini_edu_list = gemini_profile.get("education", [])
        if gemini_edu_list:
            edu_text = " ".join([f"{e.get('degree','')} {e.get('major','')} {e.get('institution','')}" for e in gemini_edu_list])
            education_profile = extract_education_profile(edu_text)
        else:
            education_profile = extract_education_profile(cv_text)
            
        # Reconstruct work experiences
        gemini_exp_list = gemini_profile.get("work_experiences", [])
        if gemini_exp_list:
            work_experiences = []
            for exp in gemini_exp_list:
                role_name = exp.get("role", "")
                from modules.nlp import _infer_work_level
                work_level = _infer_work_level(role_name)
                
                work_experiences.append({
                    "role": role_name,
                    "company": exp.get("company", "Unknown"),
                    "duration": exp.get("duration", ""),
                    "years": exp.get("years", 1.0),
                    "level": work_level
                })
        else:
            work_experiences = extract_work_experience(cv_text)
            
        total_experience_years = calculate_total_experience_years(work_experiences)
        gemini_summary = gemini_profile.get("summary", "")
        gemini_improvements = gemini_profile.get("improvements", [])
    else:
        # Fallback to local parsing
        cv_weighted_skills, cv_match_types = extract_weighted_skills(cv_text)
        education_profile = extract_education_profile(cv_text)
        work_experiences = extract_work_experience(cv_text)
        total_experience_years = calculate_total_experience_years(work_experiences)
    # ----------------------------------------

    cv_weighted_skills, skill_evidence = extract_cv_skill_evidence(
        cv_text,
        cv_weighted_skills,
        cv_match_types,
    )

    cv_experience_level = (
        work_experiences[0].get("level", "entry_level") if work_experiences else "entry_level"
    )
    detected_skills = sorted(cv_weighted_skills, key=lambda skill: (-cv_weighted_skills[skill], skill)) or extract_skills(cv_text)
    is_auto_mode = analysis_mode == "auto"
    cv_role_family = infer_cv_role_family(target_role, cv_text, cv_weighted_skills, education_profile, is_auto_mode)
    cv_signal_role_family = infer_cv_role_family("", cv_text, cv_weighted_skills, education_profile, True)
    effective_target = target_role if not is_auto_mode else "Pekerjaan paling cocok dari CV"
    target_available, target_availability_reason, target_availability_score = (
        target_available_score(target_role, jobs, cv_role_family)
        if not is_auto_mode
        else (True, "Mode otomatis memilih rekomendasi dari dataset lowongan yang tersedia.", 1.0)
    )
    suggested_target_roles = suggest_target_roles(cv_signal_role_family, detected_skills, jobs)
    suggestion_reason = build_suggestion_reason(cv_signal_role_family, suggested_target_roles)
    evidence_summary = build_evidence_summary(skill_evidence)
    target_core_evidence = core_role_evidence(cv_role_family, cv_weighted_skills, skill_evidence)
    benchmark_warnings = []
    evidence_warnings = []
    if evidence_summary["fuzzyOnly"] > evidence_summary["projectEvidence"] + evidence_summary["experienceEvidence"]:
        benchmark_warnings.append("Sebagian besar skill hanya terdeteksi fuzzy; hasil perlu ditinjau manual.")
    if evidence_summary["listedOnly"] > 6 and evidence_summary["projectEvidence"] == 0 and evidence_summary["experienceEvidence"] == 0:
        benchmark_warnings.append("Banyak skill terlihat hanya dari daftar skill tanpa bukti project/pengalaman.")
    if evidence_summary["negativeContext"] > 0:
        evidence_warnings.append("Beberapa skill muncul dalam konteks negatif dan tidak dihitung sebagai bukti kuat.")
    if target_core_evidence["required"] and not target_core_evidence["sufficient"]:
        warning_text = f"Bukti skill inti untuk target {cv_role_family} belum cukup kuat; rekomendasi role terkait tidak dipaksakan."
        benchmark_warnings.append(warning_text)
        evidence_warnings.append(warning_text)
    roadmap_family = cv_role_family if target_available else cv_signal_role_family
    preliminary_roadmap, preliminary_projects = build_career_roadmap(
        roadmap_family,
        [],
        detected_skills,
        cv_experience_level,
    )
    cv_quality_score, cv_quality_findings, rewrite_hints = audit_cv_quality(
        cv_text,
        detected_skills,
        work_experiences,
        target_role if not is_auto_mode else "",
        target_available,
    )
    log_analysis_stage(stage_timings, "parse_cv", stage_started)

    if cv_text_length < MIN_EXTRACTED_TEXT_LENGTH:
        payload = {
            "id": f"analysis-{int(time.time() * 1000)}",
            "targetRole": effective_target,
            "analysisMode": analysis_mode,
            "date": time.strftime("%d %B %Y"),
            "score": 0,
            "verdict": get_match_level(0),
            "summary": "Teks CV tidak berhasil dibaca. Pastikan file PDF bukan scan gambar.",
            "detectedSkills": [],
            "workExperiences": [],
            "totalExperienceYears": 0,
            "experienceLevel": "entry_level",
            "experienceMatch": 0,
            "missingSkills": [],
            "improvements": build_improvements([], [], None),
            "jobs": [],
            "warnings": ["PDF tidak menghasilkan teks yang cukup. Gunakan PDF teks, bukan scan gambar, atau tambahkan OCR."],
            "skillMatchTypes": {},
            "roleFamily": cv_role_family,
            "matchConfidence": "Rendah",
            "rankingReasons": [],
            "riskFlags": ["cv_text_unreadable"],
            "targetAvailable": target_available,
            "targetAvailabilityReason": target_availability_reason,
            "suggestedTargetRoles": suggested_target_roles,
            "suggestionReason": suggestion_reason,
            "roadmapSteps": preliminary_roadmap,
            "portfolioProjects": preliminary_projects,
            "cvQualityScore": cv_quality_score,
            "cvQualityFindings": cv_quality_findings,
            "rewriteHints": rewrite_hints,
            "skillEvidence": {},
            "evidenceSummary": evidence_summary,
            "targetCoreEvidence": target_core_evidence,
            "evidenceWarnings": evidence_warnings,
            "suppressedJobsCount": 0,
            "suppressionReasons": [],
            "benchmarkWarnings": benchmark_warnings,
            "_cvText": cv_text,
        }
        logger.info(
            "Analysis completed in %.2fs mode=%s target=%s jobs=%s timings=%s",
            time.perf_counter() - total_started,
            analysis_mode,
            target_role,
            0,
            {key: round(value, 2) for key, value in stage_timings.items()},
        )
        return payload

    processed_jobs = []
    stage_started = time.perf_counter()
    candidate_jobs = select_candidate_jobs(
        jobs,
        cv_weighted_skills,
        target_role,
        cv_text,
        education_profile,
        is_auto_mode,
        cv_role_family,
    )
    log_analysis_stage(stage_timings, "select_candidates", stage_started)

    stage_started = time.perf_counter()
    for job in candidate_jobs:
        title = job["title"]
        company = job["company"]
        location = job["location"]
        description = job["description"]
        job_text = job["jobText"]
        job_skills = job["jobSkills"]
        mandatory_skills = list(job.get("mandatorySkills", []))
        nice_to_have_skills = list(job.get("niceToHaveSkills", []))
        soft_skills = list(job.get("softSkills", []))
        if not mandatory_skills and not nice_to_have_skills:
            mandatory_skills = [skill for skill in job_skills if skill not in SOFT_SKILLS][:6]
            soft_skills = [skill for skill in job_skills if skill in SOFT_SKILLS][:8]
        matched_skills = sorted(set(cv_weighted_skills) & set(job_skills))
        missing_job_skills = sorted(set(job_skills) - set(cv_weighted_skills))

        skill_score = skill_match_score(cv_weighted_skills, job_skills)
        requirement_fit = requirement_fit_score(
            cv_weighted_skills,
            mandatory_skills,
            nice_to_have_skills,
            soft_skills,
        )
        job_family = job.get("jobFamily") or role_family_from_text(f"{title}. {job.get('keyword', '')}. {description[:900]}", job.get("jobDomains", []))
        role_family_score = role_family_match_score(cv_role_family, job_family)
        corpus_query = f"{target_role}. {' '.join(detected_skills[:12])}. {cv_text[:700]}"
        corpus_score = jobs_service.corpus_relevance_score(corpus_query, job)
        role_score = 0.0 if is_auto_mode else role_match_score(target_role, title, description)
        transfer_score = transferable_score(detected_skills, job_text)
        education_score = education_match_score(education_profile, job["jobDomains"])
        job_seniority = infer_job_seniority(title, description)
        job_seniority_score = seniority_match_score(cv_experience_level, job_seniority, skill_score)
        target_seniority = infer_job_seniority(target_role, target_role) if not is_auto_mode else cv_experience_level
        target_seniority_score = seniority_match_score(cv_experience_level, target_seniority, skill_score)
        seniority_score = min(job_seniority_score, target_seniority_score)
        missing_ratio = len(missing_job_skills) / len(job_skills) if job_skills else 1.0
        final_score = calculate_final_score(
            skill_score,
            corpus_score,
            role_score,
            transfer_score,
            education_score,
            missing_ratio,
            is_auto_mode,
            role_family_score=role_family_score,
            seniority_score=seniority_score,
            corpus_score=corpus_score,
            requirement_score=requirement_fit["score"],
        )
        generic_penalty, generic_cap, specificity_reasons = generic_job_adjustment(
            job,
            matched_skills,
            cv_role_family,
            job_family,
            requirement_fit,
        )
        specificity_lift = specificity_bonus(job, is_auto_mode, cv_role_family, job_family)
        final_score = max(0.0, min(1.0, final_score + specificity_lift - generic_penalty))
        if generic_cap is not None:
            final_score = min(final_score, generic_cap)
        if target_core_evidence["required"] and not target_core_evidence["sufficient"] and role_family_score >= 0.65:
            final_score = min(final_score, 0.42)
        risk_flags = []
        if role_family_score < 0.25:
            risk_flags.append("role_family_mismatch")
        if seniority_score < 0.7:
            risk_flags.append("seniority_mismatch")
        if requirement_fit["score"] < 0.25:
            risk_flags.append("weak_skill_evidence")
        if target_core_evidence["required"] and not target_core_evidence["sufficient"] and role_family_score >= 0.65:
            risk_flags.append("core_role_evidence_missing")
        if generic_penalty >= 0.10:
            risk_flags.append("generic_skill_only_match")
        ranking_reasons = build_ranking_reasons(
            matched_skills,
            role_family_score,
            corpus_score,
            education_score,
            seniority_score,
            requirement_fit,
        )
        strong_evidence, weak_evidence, missing_evidence = build_job_evidence(
            matched_skills,
            missing_job_skills,
            cv_match_types,
            role_family_score,
            corpus_score,
            requirement_fit,
            skill_evidence,
        )
        display_eligible = is_display_eligible(
            is_auto_mode,
            target_available,
            role_family_score,
            skill_score,
            corpus_score,
            role_score,
            strong_evidence,
            requirement_fit,
        )
        if target_core_evidence["required"] and not target_core_evidence["sufficient"] and role_family_score >= 0.65:
            display_eligible = False
        final_percent = round(final_score * 100)
        suppression_reasons = []
        if not display_eligible:
            if target_core_evidence["required"] and not target_core_evidence["sufficient"] and role_family_score >= 0.65:
                suppression_reasons.append("core_role_evidence_missing")
            if role_family_score < 0.25:
                suppression_reasons.append("role_family_mismatch")
            if requirement_fit["score"] < 0.25:
                suppression_reasons.append("weak_requirement_fit")
            if not suppression_reasons:
                suppression_reasons.append("display_evidence_below_threshold")

        processed_jobs.append(
            {
                "title": title.title(),
                "company": company,
                "location": location,
                "skills": job_skills,
                "mandatorySkills": mandatory_skills,
                "niceToHaveSkills": nice_to_have_skills,
                "matchedSkills": matched_skills,
                "missingSkills": missing_evidence[:10],
                "match": final_percent,
                "roleFamily": job_family,
                "matchConfidence": match_confidence(final_percent, risk_flags),
                "rankingReasons": ranking_reasons,
                "riskFlags": risk_flags,
                "strongEvidence": strong_evidence,
                "weakEvidence": weak_evidence,
                "missingEvidence": missing_evidence,
                "coreRoleEvidence": target_core_evidence,
                "jobSpecificity": round(float(job.get("jobSpecificity", 0.55)) * 100),
                "genericSkillPenalty": round(generic_penalty * 100),
                "specificityReasons": specificity_reasons,
                "evidenceBreakdown": {
                    skill: skill_evidence.get(skill, {"label": "unknown", "source": "unknown", "weight": round(cv_weighted_skills.get(skill, 1.0), 2)})
                    for skill in matched_skills
                },
                "requirementFit": {
                    "score": round(requirement_fit["score"] * 100),
                    "mandatory": round(requirement_fit["mandatoryScore"] * 100),
                    "niceToHave": round(requirement_fit["niceToHaveScore"] * 100),
                    "soft": round(requirement_fit["softScore"] * 100),
                    "mandatoryMatched": requirement_fit["mandatoryMatched"],
                    "mandatoryMissing": requirement_fit["mandatoryMissing"],
                    "niceToHaveMatched": requirement_fit["niceToHaveMatched"],
                    "niceToHaveMissing": requirement_fit["niceToHaveMissing"],
                },
                "seniorityFit": {
                    "score": round(seniority_score * 100),
                    "candidateLevel": cv_experience_level,
                    "requiredLevel": job.get("seniorityRequirement", job_seniority),
                    "targetLevel": target_seniority,
                },
                "displayEligible": display_eligible,
                "suppressionReasons": suppression_reasons,
                "detail": build_match_reason(title, matched_skills, role_score if not is_auto_mode else role_family_score, corpus_score, education_score),
                "notFitReason": build_gap_reason(
                    title,
                    matched_skills,
                    missing_job_skills,
                    role_score if not is_auto_mode else role_family_score,
                    corpus_score,
                    education_score,
                ),
                "improvements": build_job_improvements(
                    title,
                    matched_skills,
                    missing_job_skills,
                    role_score if not is_auto_mode else role_family_score,
                    corpus_score,
                    education_score,
                ),
                "description": description[:220].strip() or "Detail pekerjaan belum tersedia.",
                "scoreBreakdown": {
                    "skillMatch": round(skill_score * 100),
                    "requirementFit": round(requirement_fit["score"] * 100),
                    "semanticMatch": round(corpus_score * 100),
                    "roleMatch": round(role_score * 100),
                    "roleFamilyMatch": round(role_family_score * 100),
                    "contextMatch": round(transfer_score * 100),
                    "educationMatch": round(education_score * 100),
                    "seniorityMatch": round(seniority_score * 100),
                    "corpusRelevance": round(corpus_score * 100),
                    "jobSpecificity": round(float(job.get("jobSpecificity", 0.55)) * 100),
                    "genericSkillPenalty": round(generic_penalty * 100),
                    "missingSkillPenalty": round(min(20, missing_ratio * 20)),
                },
            }
        )
    log_analysis_stage(stage_timings, "score_jobs", stage_started)

    stage_started = time.perf_counter()
    eligible_jobs = [job for job in processed_jobs if job.get("displayEligible")]
    eligible_jobs.sort(key=lambda item: item["match"], reverse=True)
    top_jobs = eligible_jobs[:TOP_K]
    suppressed_jobs = [job for job in processed_jobs if not job.get("displayEligible")]
    suppression_counter = Counter(
        reason
        for job in suppressed_jobs
        for reason in job.get("suppressionReasons", [])
    )
    suppression_reasons = [
        f"{reason}: {count}"
        for reason, count in suppression_counter.most_common(4)
    ]
    relevant_missing = []
    for job in top_jobs:
        for skill in job["missingSkills"]:
            if skill in relevant_missing:
                continue
            if skill_relevant_to_family(skill, roadmap_family) or course_relevant_to_family(skill, roadmap_family):
                relevant_missing.append(skill)
    if not relevant_missing:
        relevant_missing = target_skill_candidates(roadmap_family, target_core_evidence, 6)
    missing_skills = relevant_missing[:10]
    best_score = top_jobs[0]["match"] if top_jobs else 0
    top_job = top_jobs[0] if top_jobs else {}
    roadmap_steps, portfolio_projects = build_career_roadmap(
        roadmap_family,
        missing_skills,
        detected_skills,
        cv_experience_level,
    )
    experience_match_score = round(
        get_experience_level_match(cv_experience_level, top_job.get("title", "")) * 100
    ) if top_jobs else 0
    summary = gemini_summary if gemini_summary else build_summary(
        target_role,
        detected_skills,
        missing_skills,
        best_score,
        education_profile,
        cv_weighted_skills,
    )
    if not is_auto_mode and target_available is False:
        summary = (
            f"{target_availability_reason} JobFit tidak menampilkan lowongan agar rekomendasi tidak menyesatkan. "
            f"Saran target yang lebih dekat dengan CV: {', '.join(suggested_target_roles[:3]) or 'belum tersedia'}."
        )
    elif target_core_evidence["required"] and not target_core_evidence["sufficient"]:
        matched_core = format_list(target_core_evidence.get("matched", []), 3, "belum ada skill inti yang cukup kuat")
        missing_core = format_list(target_core_evidence.get("missing", []), 4, "skill inti target")
        summary = (
            f"Target {target_role} tersedia di dataset, tetapi CV belum menunjukkan bukti inti yang cukup untuk role ini. "
            f"Sinyal yang terbaca baru {matched_core}, sedangkan bukti seperti {missing_core} masih perlu diperkuat. "
            f"Karena itu JobFit tidak memaksakan rekomendasi agar hasil tidak menyesatkan."
        )

    target_mismatch = (
        not is_auto_mode
        and (
            target_available is False
            or (target_core_evidence["required"] and not target_core_evidence["sufficient"])
            or not top_jobs
            or best_score < 50
        )
    )
    if target_mismatch:
        improvements = build_target_mismatch_improvements(
            target_role,
            cv_role_family,
            detected_skills,
            target_core_evidence,
            suggested_target_roles,
        )
    else:
        improvements = gemini_improvements if gemini_improvements else build_improvements(
            detected_skills,
            missing_skills,
            cv_weighted_skills,
            target_role,
            cv_role_family,
        )

    res_payload = {
        "id": new_analysis_id(),
        "targetRole": effective_target,
        "analysisMode": analysis_mode,
        "date": time.strftime("%d %B %Y"),
        "score": best_score,
        "verdict": get_match_level(best_score),
        "summary": summary,
        "roleFamily": cv_role_family,
        "matchConfidence": top_job.get("matchConfidence", match_confidence(best_score, [])),
        "rankingReasons": top_job.get("rankingReasons", []),
        "riskFlags": top_job.get("riskFlags", []),
        "targetAvailable": target_available,
        "targetAvailabilityReason": target_availability_reason,
        "suggestedTargetRoles": suggested_target_roles,
        "suggestionReason": suggestion_reason,
        "targetAvailabilityScore": round(target_availability_score * 100),
        "roadmapSteps": roadmap_steps,
        "portfolioProjects": portfolio_projects,
        "cvQualityScore": cv_quality_score,
        "cvQualityFindings": cv_quality_findings,
        "rewriteHints": rewrite_hints,
        "skillEvidence": skill_evidence,
        "evidenceSummary": evidence_summary,
        "targetCoreEvidence": target_core_evidence,
        "evidenceWarnings": evidence_warnings,
        "suppressedJobsCount": len(suppressed_jobs),
        "suppressionReasons": suppression_reasons,
        "benchmarkWarnings": benchmark_warnings,
        "detectedSkills": detected_skills,
        # K11: Expose per-skill confidence weight for UI display
        "skillConfidence": {
            skill: round(cv_weighted_skills.get(skill, 1.0), 2)
            for skill in detected_skills
        },
        "workExperiences": work_experiences,
        "totalExperienceYears": total_experience_years,
        "experienceLevel": cv_experience_level,
        "experienceMatch": experience_match_score,
        "missingSkills": missing_skills,
        "improvements": improvements,
        "jobs": top_jobs,
        "warnings": [],
        # P1: Expose per-skill match type ("exact" or "fuzzy") for UI display
        "skillMatchTypes": {
            skill: cv_match_types.get(skill, "exact")
            for skill in detected_skills
        },
        "_cvText": cv_text,
    }
    log_analysis_stage(stage_timings, "build_response", stage_started)

    if pdf_hash:
        if len(ANALYSIS_CACHE) >= MAX_ANALYSIS_CACHE_ITEMS:
            first_key = next(iter(ANALYSIS_CACHE))
            ANALYSIS_CACHE.pop(first_key, None)
        ANALYSIS_CACHE[cache_key] = copy.deepcopy(res_payload)

    logger.info(
        "Analysis completed in %.2fs mode=%s target=%s candidates=%s displayed=%s timings=%s",
        time.perf_counter() - total_started,
        analysis_mode,
        target_role,
        len(candidate_jobs),
        len(top_jobs),
        {key: round(value, 2) for key, value in stage_timings.items()},
    )
    return res_payload
