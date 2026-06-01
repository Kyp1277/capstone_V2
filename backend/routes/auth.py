import logging
from typing import Optional

from modules import config as _config  # noqa: F401
from fastapi import APIRouter, Body, Header, HTTPException

from modules import auth_service, database
from modules.rate_limit import enforce_rate_limit


logger = logging.getLogger("jobfit.routes.auth")
router = APIRouter(prefix="/api/auth")


@router.post("/register")
def register(payload: dict = Body(...)):
    data = auth_service.validate_auth_payload(payload, require_name=True)
    enforce_rate_limit("register", data["email"], limit=5, window_seconds=10 * 60)

    try:
        user = database.create_or_update_unverified_user(data["name"], data["email"], data["password"])
        if not user:
            raise HTTPException(status_code=409, detail="Email sudah terdaftar. Silakan masuk dengan akun tersebut.")
        return auth_service.issue_register_otp(user)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Registration failed.")
        raise HTTPException(status_code=500, detail="Registrasi gagal diproses.") from error


@router.post("/verify-otp")
def verify_otp(payload: dict = Body(...)):
    verification_id = str(payload.get("verificationId") or "").strip()
    email = str(payload.get("email") or "").strip().lower()
    otp = str(payload.get("otp") or "").strip()

    if not verification_id or "@" not in email or len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="Kode verifikasi tidak valid.")
    enforce_rate_limit("verify_otp", email, limit=8, window_seconds=10 * 60)

    try:
        result = database.verify_email_otp(verification_id, email, otp)
        if not result["ok"]:
            messages = {
                "not_found": "Kode verifikasi tidak ditemukan.",
                "consumed": "Kode verifikasi sudah digunakan.",
                "expired": "Kode verifikasi sudah kedaluwarsa. Kirim ulang kode.",
                "too_many_attempts": "Terlalu banyak percobaan kode. Kirim ulang kode.",
                "invalid": "Kode verifikasi salah.",
            }
            raise HTTPException(status_code=400, detail=messages.get(result["reason"], "Kode verifikasi tidak valid."))
        return auth_service.auth_response(result["user"])
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("OTP verification failed.")
        raise HTTPException(status_code=500, detail="Verifikasi OTP gagal diproses.") from error


@router.post("/resend-otp")
def resend_otp(payload: dict = Body(...)):
    email = str(payload.get("email") or "").strip().lower()

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Masukkan alamat email yang valid.")
    enforce_rate_limit("resend_otp", email, limit=3, window_seconds=10 * 60)

    try:
        otp_payload, reason = database.create_otp_for_unverified_email(email)
        if reason == "not_found":
            raise HTTPException(status_code=404, detail="Akun belum ditemukan. Silakan daftar ulang.")
        if reason == "verified":
            raise HTTPException(status_code=409, detail="Email sudah diverifikasi. Silakan masuk.")
        try:
            auth_service.send_otp_email(otp_payload["email"], otp_payload["otp"])
            return auth_service.build_otp_response(otp_payload, True)
        except Exception as error:
            if auth_service.is_development():
                logger.warning("OTP resend email delivery failed; using development fallback: %s", error)
                return auth_service.build_otp_response(otp_payload, False)
            logger.exception("OTP resend email delivery failed.")
            raise HTTPException(status_code=500, detail="Email OTP tidak terkirim. Coba beberapa saat lagi.") from error
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("OTP resend failed.")
        raise HTTPException(status_code=500, detail="Kirim ulang OTP gagal diproses.") from error


@router.post("/login")
def login(payload: dict = Body(...)):
    data = auth_service.validate_auth_payload(payload, require_name=False)
    enforce_rate_limit("login", data["email"], limit=8, window_seconds=10 * 60)

    try:
        user = database.authenticate_user(data["email"], data["password"])
        if not user:
            raise HTTPException(status_code=401, detail="Email atau password tidak cocok.")
        if not user.get("emailVerified"):
            raise HTTPException(status_code=403, detail="Email belum diverifikasi.")

        return auth_service.auth_response(user)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Login failed.")
        raise HTTPException(status_code=500, detail="Login gagal diproses.") from error


@router.get("/me")
def me(authorization: Optional[str] = Header(None)):
    return {"user": auth_service.require_authenticated_user(authorization)}


@router.patch("/me")
def update_profile(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    user = auth_service.require_authenticated_user(authorization)
    name = str(payload.get("name") or "").strip()

    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Nama wajib diisi minimal 2 karakter.")

    try:
        return {"user": database.update_user(user["id"], name)}
    except Exception as error:
        logger.exception("Profile update failed.")
        raise HTTPException(status_code=500, detail="Profil gagal diperbarui.") from error


@router.post("/change-password")
def change_password(payload: dict = Body(...), authorization: Optional[str] = Header(None)):
    user = auth_service.require_authenticated_user(authorization)
    current_password = str(payload.get("currentPassword") or "")
    new_password = str(payload.get("newPassword") or "")
    confirm_password = str(payload.get("confirmPassword") or "")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password baru minimal 6 karakter.")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Konfirmasi password baru tidak sama.")

    try:
        if not database.change_user_password(user["id"], current_password, new_password):
            raise HTTPException(status_code=400, detail="Password saat ini tidak cocok.")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Password change failed.")
        raise HTTPException(status_code=500, detail="Password gagal diganti.") from error


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    try:
        database.delete_session(auth_service.bearer_token(authorization))
    except Exception:
        logger.exception("Logout failed.")

    return {"ok": True}
