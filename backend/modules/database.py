from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import hmac
import json
import os
import secrets
import uuid

from modules.env_loader import load_env_file


ROOT = Path(__file__).resolve().parents[1]
load_env_file(ROOT / ".env")

PASSWORD_ITERATIONS = 210_000
SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "30"))
OTP_MINUTES = int(os.environ.get("OTP_MINUTES", "10"))
MAX_OTP_ATTEMPTS = int(os.environ.get("MAX_OTP_ATTEMPTS", "5"))


def get_database_url():
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def get_connection():
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL wajib diisi untuk fitur akun dan riwayat.")

    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError(
            "Dependency PostgreSQL belum tersedia. Jalankan `pip install -r backend/requirements.txt`."
        ) from error

    return psycopg.connect(database_url)


def ensure_database_schema():
    schema_path = ROOT / "database" / "schema.sql"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_path.read_text(encoding="utf-8"))
        connection.commit()


def cleanup_expired_records():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sessions WHERE expires_at <= NOW()")
            cursor.execute(
                """
                UPDATE email_otps
                SET consumed_at = NOW()
                WHERE expires_at <= NOW() AND consumed_at IS NULL
                """
            )
        connection.commit()


def normalize_email(email):
    return str(email or "").strip().lower()


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, digest = str(stored_hash).split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(candidate, digest)


def public_user(row):
    if not row:
        return None

    return {
        "id": str(row["id"]),
        "name": row["name"],
        "email": row["email"],
        "emailVerified": bool(row.get("email_verified", False)),
        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
    }


def create_user(name, email, password):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    normalized_email = normalize_email(email)
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, name, email, email_verified, created_at
                """,
                (str(name).strip(), normalized_email, hash_password(password)),
            )
            row = cursor.fetchone()
        connection.commit()

    return public_user(row)


def create_or_update_unverified_user(name, email, password):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    normalized_email = normalize_email(email)
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, email_verified
                FROM users
                WHERE email = %s
                """,
                (normalized_email,),
            )
            existing = cursor.fetchone()

            if existing and existing["email_verified"]:
                return None

            if existing:
                cursor.execute(
                    """
                    UPDATE users
                    SET name = %s, password_hash = %s, updated_at = NOW()
                    WHERE email = %s
                    RETURNING id, name, email, email_verified, created_at
                    """,
                    (str(name).strip(), hash_password(password), normalized_email),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (name, email, password_hash, email_verified)
                    VALUES (%s, %s, %s, FALSE)
                    RETURNING id, name, email, email_verified, created_at
                    """,
                    (str(name).strip(), normalized_email, hash_password(password)),
                )

            row = cursor.fetchone()
        connection.commit()

    return public_user(row)


def get_user_by_email(email):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, email, email_verified, created_at
                FROM users
                WHERE email = %s
                """,
                (normalize_email(email),),
            )
            row = cursor.fetchone()

    return public_user(row)


def authenticate_user(email, password):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, email, password_hash, email_verified, created_at
                FROM users
                WHERE email = %s
                """,
                (normalize_email(email),),
            )
            row = cursor.fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        return None

    return public_user(row)


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sessions (token, user_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (token, user_id, expires_at),
            )
        connection.commit()

    return token, expires_at


def create_email_otp(user_id, email, purpose="register"):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    otp = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_MINUTES)
    normalized_email = normalize_email(email)

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE email_otps
                SET consumed_at = NOW()
                WHERE user_id = %s AND purpose = %s AND consumed_at IS NULL
                """,
                (user_id, purpose),
            )
            cursor.execute(
                """
                INSERT INTO email_otps (user_id, email, otp_hash, purpose, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, expires_at
                """,
                (user_id, normalized_email, hash_password(otp), purpose, expires_at),
            )
            row = cursor.fetchone()
        connection.commit()

    return {
        "verificationId": str(row["id"]),
        "email": row["email"],
        "expiresAt": row["expires_at"].isoformat(),
        "otp": otp,
    }


def verify_email_otp(verification_id, email, otp, purpose="register"):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, user_id, email, otp_hash, expires_at, attempts, consumed_at
                FROM email_otps
                WHERE id = %s AND email = %s AND purpose = %s
                """,
                (verification_id, normalize_email(email), purpose),
            )
            row = cursor.fetchone()

            if not row:
                return {"ok": False, "reason": "not_found"}

            if row["consumed_at"] is not None:
                return {"ok": False, "reason": "consumed"}

            if row["expires_at"] <= datetime.now(timezone.utc):
                return {"ok": False, "reason": "expired"}

            if int(row["attempts"] or 0) >= MAX_OTP_ATTEMPTS:
                return {"ok": False, "reason": "too_many_attempts"}

            if not verify_password(str(otp), row["otp_hash"]):
                cursor.execute(
                    """
                    UPDATE email_otps
                    SET attempts = attempts + 1
                    WHERE id = %s
                    """,
                    (verification_id,),
                )
                connection.commit()
                return {"ok": False, "reason": "invalid"}

            cursor.execute(
                """
                UPDATE email_otps
                SET consumed_at = NOW()
                WHERE id = %s
                """,
                (verification_id,),
            )
            cursor.execute(
                """
                UPDATE users
                SET email_verified = TRUE, updated_at = NOW()
                WHERE id = %s
                RETURNING id, name, email, email_verified, created_at
                """,
                (row["user_id"],),
            )
            user_row = cursor.fetchone()
        connection.commit()

    return {"ok": True, "user": public_user(user_row)}


def create_otp_for_unverified_email(email, purpose="register"):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, email, email_verified, created_at
                FROM users
                WHERE email = %s
                """,
                (normalize_email(email),),
            )
            user = cursor.fetchone()

    if not user:
        return None, "not_found"

    if user["email_verified"]:
        return None, "verified"

    return create_email_otp(user["id"], user["email"], purpose), None


def get_user_by_token(token):
    if not token:
        return None

    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("DELETE FROM sessions WHERE expires_at <= NOW()")
            cursor.execute(
                """
                SELECT users.id, users.name, users.email, users.email_verified, users.created_at
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = %s AND sessions.expires_at > NOW()
                """,
                (token,),
            )
            row = cursor.fetchone()
        connection.commit()

    return public_user(row)


def delete_session(token):
    if not token:
        return

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sessions WHERE token = %s", (token,))
        connection.commit()


def update_user(user_id, name):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE users
                SET name = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, name, email, email_verified, created_at
                """,
                (str(name).strip(), user_id),
            )
            row = cursor.fetchone()
        connection.commit()

    return public_user(row)


def change_user_password(user_id, current_password, new_password):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if not row or not verify_password(current_password, row["password_hash"]):
                return False

            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (hash_password(new_password), user_id),
            )
        connection.commit()

    return True


def save_analysis(user_id, result, cv_text):
    try:
        from psycopg.types.json import Json
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    analysis_id = str(result.get("id") or f"analysis-{uuid.uuid4()}")
    result = dict(result)
    result["id"] = analysis_id

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analyses (
                    id, user_id, target_role, analysis_mode, score, verdict, cv_text, result_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    target_role = EXCLUDED.target_role,
                    analysis_mode = EXCLUDED.analysis_mode,
                    score = EXCLUDED.score,
                    verdict = EXCLUDED.verdict,
                    cv_text = EXCLUDED.cv_text,
                    result_json = EXCLUDED.result_json
                """,
                (
                    analysis_id,
                    user_id,
                    result.get("targetRole", "Analisis CV"),
                    result.get("analysisMode", "targeted"),
                    int(result.get("score") or 0),
                    result.get("verdict", "Analisis Selesai"),
                    cv_text,
                    Json(result),
                ),
            )
        connection.commit()

    return result


def list_user_analyses(user_id, limit=50):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, target_role, analysis_mode, score, verdict, result_json, created_at
                FROM analyses
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()

    return [analysis_list_item(row) for row in rows]


def get_user_analysis(user_id, analysis_id):
    try:
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Dependency PostgreSQL belum tersedia.") from error

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT result_json, created_at
                FROM analyses
                WHERE user_id = %s AND id = %s
                """,
                (user_id, analysis_id),
            )
            row = cursor.fetchone()

    if not row:
        return None

    return analysis_detail(row)


def analysis_list_item(row):
    result = parse_result_json(row["result_json"])
    created_at = row["created_at"]
    result["id"] = row["id"]
    result["date"] = result.get("date") or format_date(created_at)
    result["targetRole"] = result.get("targetRole") or row["target_role"]
    result["analysisMode"] = result.get("analysisMode") or row["analysis_mode"]
    result["score"] = int(result.get("score") or row["score"] or 0)
    result["verdict"] = result.get("verdict") or row["verdict"]
    result["status"] = "Selesai"
    return result


def analysis_detail(row):
    result = parse_result_json(row["result_json"])
    if "date" not in result:
        result["date"] = format_date(row["created_at"])
    return result


def parse_result_json(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}


def format_date(value):
    if not value:
        return ""
    return value.strftime("%d %B %Y")
