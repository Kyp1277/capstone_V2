import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
LOCAL_PACKAGES = PROJECT_ROOT / ".codex-python-packages"
if LOCAL_PACKAGES.exists():
    sys.path.append(str(LOCAL_PACKAGES))
sys.path.insert(0, str(ROOT))

import api
from modules import analysis_service, auth_service, database

auth_service.send_otp_email = lambda email, otp: (_ for _ in ()).throw(RuntimeError("test otp fallback"))


class FakeUpload:
    filename = "cv.pdf"

    async def read(self):
        return b"%PDF-1.4 fake contract payload"


class MonkeyPatch:
    def __init__(self):
        self.items = []

    def setattr(self, obj, name, value):
        self.items.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, value in reversed(self.items):
            setattr(obj, name, value)


def unique_email():
    return f"contract-{uuid.uuid4().hex[:12]}@jobfit.test"


def cleanup(email):
    try:
        with database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            connection.commit()
    except Exception:
        pass


def register_user(email, password="secret123"):
    payload = {
        "name": "Contract User",
        "email": email,
        "password": password,
    }
    return api.register(payload)


def verify_registered_user(registered):
    return api.verify_otp(
        {
            "verificationId": registered["verificationId"],
            "email": registered["email"],
            "otp": registered["devOtp"],
        }
    )


def test_schema_idempotent_and_jobs_intact():
    database.ensure_database_schema()
    database.ensure_database_schema()

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM jobs")
            jobs_count = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'sessions', 'analyses', 'email_otps')
                ORDER BY table_name
                """
            )
            tables = [row[0] for row in cursor.fetchall()]

    assert jobs_count == 10785, f"Expected 10785 jobs, got {jobs_count}"
    assert tables == ["analyses", "email_otps", "sessions", "users"], tables


def test_auth_contract():
    email = unique_email()
    cleanup(email)

    try:
        registered = register_user(email)
        assert registered["verificationId"]
        assert registered["email"] == email
        assert registered["devOtp"]

        try:
            api.login({"email": email, "password": "secret123"})
            raise AssertionError("Unverified login should fail")
        except api.HTTPException as error:
            assert error.status_code == 403

        verified = verify_registered_user(registered)
        assert verified["token"]
        assert verified["user"]["email"] == email
        assert verified["user"]["emailVerified"] is True

        try:
            register_user(email)
            raise AssertionError("Duplicate verified email should fail")
        except api.HTTPException as error:
            assert error.status_code == 409

        logged_in = api.login({"email": email, "password": "secret123"})
        assert logged_in["token"]
        assert logged_in["user"]["email"] == email
        with database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT token FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                    (logged_in["user"]["id"],),
                )
                stored_token = cursor.fetchone()[0]
        assert stored_token != logged_in["token"]
        assert stored_token == database.hash_session_token(logged_in["token"])

        try:
            api.login({"email": email, "password": "wrong123"})
            raise AssertionError("Invalid login should fail")
        except api.HTTPException as error:
            assert error.status_code == 401

        user = api.me(f"Bearer {logged_in['token']}")["user"]
        assert user["email"] == email

        try:
            api.me("Bearer invalid-token")
            raise AssertionError("Invalid token should fail")
        except api.HTTPException as error:
            assert error.status_code == 401
    finally:
        cleanup(email)


def test_otp_wrong_expired_and_resend_contract():
    email = unique_email()
    cleanup(email)

    try:
        registered = register_user(email)

        try:
            api.verify_otp(
                {
                    "verificationId": registered["verificationId"],
                    "email": email,
                    "otp": "000000" if registered["devOtp"] != "000000" else "111111",
                }
            )
            raise AssertionError("Wrong OTP should fail")
        except api.HTTPException as error:
            assert error.status_code == 400

        with database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT attempts FROM email_otps WHERE id = %s", (registered["verificationId"],))
                attempts = cursor.fetchone()[0]
        assert attempts == 1

        with database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE email_otps SET expires_at = NOW() - INTERVAL '1 minute' WHERE id = %s",
                    (registered["verificationId"],),
                )
            connection.commit()

        try:
            api.verify_otp(
                {
                    "verificationId": registered["verificationId"],
                    "email": email,
                    "otp": registered["devOtp"],
                }
            )
            raise AssertionError("Expired OTP should fail")
        except api.HTTPException as error:
            assert error.status_code == 400

        resent = api.resend_otp({"email": email})
        assert resent["verificationId"] != registered["verificationId"]
        assert resent["devOtp"]

        try:
            api.verify_otp(
                {
                    "verificationId": registered["verificationId"],
                    "email": email,
                    "otp": registered["devOtp"],
                }
            )
            raise AssertionError("Old OTP should fail after resend")
        except api.HTTPException as error:
            assert error.status_code == 400

        verified = verify_registered_user(resent)
        assert verified["token"]
    finally:
        cleanup(email)


def test_analysis_persistence_contract():
    email = unique_email()
    cleanup(email)
    monkeypatch = MonkeyPatch()

    try:
        session = verify_registered_user(register_user(email))
        token = session["token"]
        analysis_id = f"analysis-{uuid.uuid4().hex[:12]}"

        def fake_analyze_cv_file(pdf_path, target_role, analysis_mode):
            return {
                "id": analysis_id,
                "targetRole": target_role,
                "analysisMode": analysis_mode,
                "date": "23 Mei 2026",
                "score": 91,
                "verdict": "Kecocokan Sangat Tinggi",
                "summary": "Synthetic CV cocok untuk backend engineer.",
                "detectedSkills": ["python", "fastapi", "postgresql"],
                "workExperiences": [],
                "totalExperienceYears": 2,
                "experienceLevel": "mid_level",
                "experienceMatch": 88,
                "missingSkills": ["docker"],
                "improvements": ["Tambahkan deployment Docker."],
                "jobs": [
                    {
                        "title": "Backend Engineer",
                        "company": "JobFit",
                        "match": 91,
                        "matchedSkills": ["python", "fastapi"],
                        "missingSkills": ["docker"],
                        "scoreBreakdown": {"skillMatch": 90},
                    }
                ],
                "warnings": [],
                "_cvText": "Python FastAPI PostgreSQL synthetic CV text",
            }

        monkeypatch.setattr(analysis_service, "analyze_cv_file", fake_analyze_cv_file)
        response = asyncio.run(
            api.create_analysis(FakeUpload(), "Backend Engineer", "targeted", f"Bearer {token}")
        )

        assert response["id"] == analysis_id
        assert "_cvText" not in response

        history = api.list_analyses(f"Bearer {token}")["analyses"]
        assert any(item["id"] == analysis_id for item in history)

        detail = api.get_analysis(analysis_id, f"Bearer {token}")
        assert detail["id"] == analysis_id
        assert detail["jobs"][0]["title"] == "Backend Engineer"

        with database.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT cv_text FROM analyses WHERE id = %s", (analysis_id,))
                cv_text = cursor.fetchone()[0]
        assert "FastAPI" in cv_text
    finally:
        monkeypatch.undo()
        cleanup(email)


def test_analysis_without_token_still_works():
    monkeypatch = MonkeyPatch()

    try:
        def fake_analyze_cv_file(pdf_path, target_role, analysis_mode):
            return {
                "id": "analysis-no-token",
                "targetRole": target_role,
                "analysisMode": analysis_mode,
                "date": "23 Mei 2026",
                "score": 70,
                "verdict": "Kecocokan Tinggi",
                "summary": "No token compatibility response.",
                "detectedSkills": ["python"],
                "workExperiences": [],
                "totalExperienceYears": 0,
                "experienceLevel": "entry_level",
                "experienceMatch": 0,
                "missingSkills": [],
                "improvements": [],
                "jobs": [],
                "warnings": [],
                "_cvText": "No token CV text",
            }

        monkeypatch.setattr(analysis_service, "analyze_cv_file", fake_analyze_cv_file)
        response = asyncio.run(api.create_analysis(FakeUpload(), "Backend Engineer", "targeted", None))
        assert response["id"] == "analysis-no-token"
        assert "_cvText" not in response
    finally:
        monkeypatch.undo()


def run_all():
    tests = [
        test_schema_idempotent_and_jobs_intact,
        test_auth_contract,
        test_otp_wrong_expired_and_resend_contract,
        test_analysis_persistence_contract,
        test_analysis_without_token_still_works,
    ]

    for test in tests:
        test()
        print(f"OK {test.__name__}")

    print("ALL DATABASE CONTRACT TESTS PASSED")


if __name__ == "__main__":
    run_all()
