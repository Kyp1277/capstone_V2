"""
Assertion-based test suite for work experience extraction.
Exit code 0 = all tests passed.
Exit code 1 = at least one assertion failed.
"""

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from nlp import (
    extract_work_experience,
    calculate_total_experience_years,
    get_experience_level_match,
    _infer_work_level,
)


# =========================================
# SYNTHETIC CV TEST DATA  (unchanged)
# =========================================

SYNTHETIC_CV_1 = """
JOHN DOE
john.doe@email.com | 08123456789 | Jakarta

PENGALAMAN KERJA

Senior Backend Developer - PT Teknologi Indonesia (2020 - 2024)
Bertanggung jawab untuk arsitektur dan development sistem backend utama.
Menggunakan Python, Django, PostgreSQL, Docker, dan Kubernetes.
Memimpin team 5 developer junior.

Mid Level Backend Developer - PT Digital Solutions (2018 - 2020)
Mengembangkan REST API menggunakan FastAPI dan Node.js.
Database management menggunakan MySQL dan MongoDB.
Collaborating dengan frontend team untuk integration.

Junior Developer - Startup Tech (2017 - 2018)
Internship menjadi full-time position sebagai junior developer.
Belajar Python, JavaScript, dan Git workflow.
Membantu maintenance aplikasi legacy system.

PENDIDIKAN

S1 Teknik Informatika - Universitas Indonesia (2013 - 2017)

SKILL
Python, JavaScript, Django, FastAPI, React, PostgreSQL, Docker, Kubernetes
"""

SYNTHETIC_CV_2 = """
JANE SMITH
jane.smith@gmail.com | 08987654321

PROFESSIONAL EXPERIENCE

Manager HR & Recruitment - PT Konsultan HR (Jan 2019 - Current)
Mengelola departemen HR dengan team 8 orang.
Responsible untuk recruitment, training, dan performance management.
Implementasi HR system baru menggunakan cloud technology.

HR Specialist - Perusahaan Retail Indonesia (Feb 2016 - Dec 2018)
Administration, payroll, dan employee benefits management.
Coordinate training programs dan employee development.

HR Officer - SME Indonesia (Jul 2014 - Jan 2016)
Entry level HR position handling general admin tasks.
Employee database management dan document handling.

EDUCATION

Bachelor in Human Resource Management - Universitas Diponegoro

SKILLS
Microsoft Office, HR system, Payroll, Recruitment, Training, Effective Communication
"""

SYNTHETIC_CV_3 = """
RESUME - ANDI PRATAMA

WORK HISTORY

Project Manager - Construction PT Bangun Sentosa (2019-2024)
Senior project engineer managing multiple construction projects.
Budget management, risk assessment, team coordination.
Site supervisor untuk project senilai 50 milyar rupiah.

Site Engineer - Konsultan Teknik Sipil (2016-2019)
Technical drawing menggunakan AutoCAD Civil 3D.
Quantity surveyor dan cost estimator.
Coordinate dengan construction team dan architect.

Junior Engineer - Firma Arsitek (2014-2016)
Drafting dan technical support.
Site inspection dan monitoring.

EDUCATION
S1 Teknik Sipil - ITB

SKILLS
AutoCAD, Civil 3D, Project Management, Site Engineering, Microsoft Excel
"""

# =========================================
# NOISE STRINGS THAT MUST NEVER APPEAR
# =========================================
FORBIDDEN_POSITIONS = [
    "s1 teknik informatika",
    "s1 teknik sipil",
    "bachelor in human resource management",
    "python",
    "javascript",
    "django",
    "fastapi",
    "react",
    "postgresql",
    "docker",
    "kubernetes",
    "autocad",
    "civil 3d",
    "microsoft office",
    "hr system",
    "payroll",
]

FORBIDDEN_COMPANIES = [
    "universitas indonesia",
    "universitas diponegoro",
    "itb",
]


# =========================================
# HELPERS
# =========================================

_failures = []


def _assert(condition, message):
    if not condition:
        frame = sys._getframe(1)
        loc = f"{Path(frame.f_code.co_filename).name}:{frame.f_lineno}"
        _failures.append(f"  FAIL [{loc}] {message}")
        print(f"  ❌ FAIL: {message}")
    else:
        print(f"  ✅ OK:   {message}")


def _positions(experiences):
    return [e["position"].lower() for e in experiences]


def _companies(experiences):
    return [e["company"].lower() for e in experiences]


def _assert_no_noise(experiences, label):
    positions = _positions(experiences)
    companies = _companies(experiences)

    for forbidden in FORBIDDEN_POSITIONS:
        for pos in positions:
            _assert(
                forbidden not in pos,
                f"[{label}] Noise in position: '{pos}' should not contain '{forbidden}'",
            )

    for forbidden in FORBIDDEN_COMPANIES:
        for comp in companies:
            _assert(
                forbidden not in comp,
                f"[{label}] Noise in company: '{comp}' should not contain '{forbidden}'",
            )


# =========================================
# TEST 1 – EXTRACTION COUNT & NO NOISE
# =========================================

def test_extract_work_experience():
    print("\n" + "=" * 70)
    print("TEST 1: EXTRACT WORK EXPERIENCE — COUNT & NOISE CHECK")
    print("=" * 70)

    cases = [
        ("CV1 - Backend Developer", SYNTHETIC_CV_1, 3),
        ("CV2 - HR Manager",        SYNTHETIC_CV_2, 3),
        ("CV3 - Project Manager",   SYNTHETIC_CV_3, 3),
    ]

    for label, cv_text, expected_count in cases:
        print(f"\n  [{label}]")
        exps = extract_work_experience(cv_text)

        _assert(
            len(exps) == expected_count,
            f"Expected {expected_count} experiences, got {len(exps)}: "
            + str([e['position'] for e in exps]),
        )

        _assert_no_noise(exps, label)

        # Every entry must have non-empty position, company, and duration
        for exp in exps:
            _assert(bool(exp.get("position")),  f"[{label}] Entry missing position: {exp}")
            _assert(bool(exp.get("company")),   f"[{label}] Entry missing company:  {exp}")
            _assert(bool(exp.get("duration")),  f"[{label}] Entry missing duration: {exp}")
            _assert(bool(exp.get("level")),     f"[{label}] Entry missing level:    {exp}")


# =========================================
# TEST 2 – SPECIFIC POSITION / COMPANY VALUES
# =========================================

def test_specific_entries():
    print("\n" + "=" * 70)
    print("TEST 2: SPECIFIC POSITION & COMPANY VALUES")
    print("=" * 70)

    # CV 1
    exps1 = extract_work_experience(SYNTHETIC_CV_1)
    positions1 = _positions(exps1)
    companies1 = _companies(exps1)

    _assert("senior backend developer" in positions1, "CV1: Senior Backend Developer present")
    _assert("mid level backend developer" in positions1, "CV1: Mid Level Backend Developer present")
    _assert("junior developer" in positions1, "CV1: Junior Developer present")
    _assert(any("pt teknologi indonesia" in c for c in companies1), "CV1: PT Teknologi Indonesia present")
    _assert(any("pt digital solutions" in c for c in companies1), "CV1: PT Digital Solutions present")
    _assert(any("startup tech" in c for c in companies1), "CV1: Startup Tech present")

    # CV 2
    exps2 = extract_work_experience(SYNTHETIC_CV_2)
    positions2 = _positions(exps2)

    _assert(any("hr" in p for p in positions2), "CV2: at least one HR position present")
    _assert("hr officer" in positions2, "CV2: HR Officer present")

    # CV 3
    exps3 = extract_work_experience(SYNTHETIC_CV_3)
    positions3 = _positions(exps3)

    _assert(any("project manager" in p for p in positions3), "CV3: Project Manager present")
    _assert(any("site engineer" in p for p in positions3), "CV3: Site Engineer present")
    _assert(any("junior engineer" in p for p in positions3), "CV3: Junior Engineer present")


# =========================================
# TEST 3 – LEVEL INFERENCE
# =========================================

def test_experience_level_inference():
    print("\n" + "=" * 70)
    print("TEST 3: EXPERIENCE LEVEL INFERENCE")
    print("=" * 70)

    cases = [
        ("CEO",                      "senior_manager"),
        ("Director of Engineering",  "senior_manager"),
        ("Senior Manager",           "senior_manager"),
        ("Senior Backend Developer", "senior"),
        ("Lead Developer",           "senior"),
        ("Mid Level Developer",      "mid_level"),
        ("Staff Developer",          "mid_level"),
        ("Junior Developer",         "junior"),
        ("Intern",                   "entry_level"),
        ("Apprentice",               "entry_level"),
    ]

    for title, expected_level in cases:
        actual = _infer_work_level(title)
        _assert(
            actual == expected_level,
            f"_infer_work_level('{title}') = '{actual}', expected '{expected_level}'",
        )


# =========================================
# TEST 4 – TOTAL EXPERIENCE YEARS
# =========================================

def test_total_experience_calculation():
    print("\n" + "=" * 70)
    print("TEST 4: TOTAL EXPERIENCE YEARS")
    print("=" * 70)

    cases = [
        ("CV1", SYNTHETIC_CV_1, 4, 9),   # 4+2+1 = 7 but current-year drift ok; range 4–9
        ("CV2", SYNTHETIC_CV_2, 4, 14),  # Jan2019-now + ~3y + ~2y
        ("CV3", SYNTHETIC_CV_3, 4, 12),  # 5+3+2 = 10; range 4–12
    ]

    for label, cv_text, min_years, max_years in cases:
        exps = extract_work_experience(cv_text)
        total = calculate_total_experience_years(exps)
        _assert(
            min_years <= total <= max_years,
            f"[{label}] Total experience {total} years not in expected range [{min_years}, {max_years}]",
        )


# =========================================
# TEST 5 – EXPERIENCE LEVEL MATCH
# =========================================

def test_experience_level_matching():
    print("\n" + "=" * 70)
    print("TEST 5: EXPERIENCE LEVEL MATCHING")
    print("=" * 70)

    # Senior CV vs Senior Job → full match
    score = get_experience_level_match("senior", "Senior Backend Engineer")
    _assert(score == 1.0, f"Senior vs Senior Job: expected 1.0, got {score}")

    # Senior CV vs Junior Job → full match (over-qualified counts as match)
    score = get_experience_level_match("senior", "Junior Developer")
    _assert(score == 1.0, f"Senior vs Junior Job: expected 1.0, got {score}")

    # Junior CV vs Senior Job → partial/low match
    score = get_experience_level_match("junior", "Senior Backend Engineer")
    _assert(score < 1.0, f"Junior vs Senior Job: expected < 1.0, got {score}")
    _assert(score >= 0.3, f"Junior vs Senior Job: expected >= 0.3, got {score}")

    # Entry-level CV vs any job → 1.0 (no job level context → default match)
    score = get_experience_level_match("entry_level", "Some Position")
    _assert(score == 1.0, f"Entry-level vs untagged job: expected 1.0, got {score}")


# =========================================
# TEST 6 – NEGATIVE: NO SECTION HEADER
# =========================================

def test_no_section_header():
    print("\n" + "=" * 70)
    print("TEST 6: NO SECTION HEADER → EMPTY RESULT")
    print("=" * 70)

    bare_text = """
    John Doe
    john@example.com

    Python Developer - PT ABC (2020 - 2023)
    """
    exps = extract_work_experience(bare_text)
    _assert(
        exps == [],
        f"Without an experience section header, result should be empty. Got: {exps}",
    )


# =========================================
# TEST 7 – NEGATIVE: EDUCATION/SKILL NOISE
# =========================================

def test_noise_not_extracted():
    print("\n" + "=" * 70)
    print("TEST 7: EDUCATION & SKILL LINES MUST NOT BE EXTRACTED")
    print("=" * 70)

    noisy_cv = """
    NAMA: Budi

    PENGALAMAN KERJA

    Software Engineer - PT Maju (2021 - 2023)

    PENDIDIKAN
    S1 Teknik Informatika - Universitas Indonesia (2017 - 2021)

    SKILL
    Python, JavaScript, React, PostgreSQL, Docker
    """

    exps = extract_work_experience(noisy_cv)
    positions = _positions(exps)

    _assert(len(exps) == 1, f"Should find exactly 1 experience, got {len(exps)}: {exps}")
    _assert("software engineer" in positions, "Software Engineer should be extracted")

    for pos in positions:
        _assert(
            "teknik informatika" not in pos and "universitas" not in pos,
            f"Education line must not appear as position: '{pos}'",
        )
        _assert(
            not any(sk in pos for sk in ["python", "javascript", "react", "postgresql", "docker"]),
            f"Skill list must not appear as position: '{pos}'",
        )


# =========================================
# MAIN RUNNER
# =========================================

if __name__ == "__main__":
    print("\n🔍 WORK EXPERIENCE EXTRACTION TEST SUITE")
    print("=" * 70)

    test_extract_work_experience()
    test_specific_entries()
    test_experience_level_inference()
    test_total_experience_calculation()
    test_experience_level_matching()
    test_no_section_header()
    test_noise_not_extracted()

    print("\n" + "=" * 70)
    if _failures:
        print(f"❌ {len(_failures)} ASSERTION(S) FAILED:\n")
        for msg in _failures:
            print(msg)
        print("=" * 70 + "\n")
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED!")
        print("=" * 70 + "\n")
        sys.exit(0)