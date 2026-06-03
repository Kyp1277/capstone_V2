from email.message import EmailMessage
import json
import logging
import os
import smtplib
from urllib import request
from urllib.error import HTTPError

from fastapi import HTTPException

from modules import config, database


logger = logging.getLogger("jobfit.auth")


def bearer_token(authorization):
    if not authorization or not isinstance(authorization, str):
        return ""

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return ""

    return authorization[len(prefix) :].strip()


def current_user_from_header(authorization):
    token = bearer_token(authorization)
    if not token:
        return None

    try:
        return database.get_user_by_token(token)
    except Exception:
        logger.exception("Failed to load authenticated user.")
        return None


def optional_authenticated_user(authorization):
    if not authorization or not isinstance(authorization, str):
        return None

    token = bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Sesi login tidak valid. Silakan masuk ulang.")

    user = database.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sesi login tidak valid. Silakan masuk ulang.")

    return user


def require_authenticated_user(authorization):
    user = current_user_from_header(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sesi login tidak valid. Silakan masuk ulang.")
    return user


def validate_auth_payload(payload, require_name=False):
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    name = str(payload.get("name") or "").strip()

    if require_name and len(name) < 2:
        raise HTTPException(status_code=400, detail="Nama wajib diisi minimal 2 karakter.")

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Masukkan alamat email yang valid.")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password minimal 6 karakter.")

    return {"name": name, "email": email, "password": password}


def auth_response(user):
    token, expires_at = database.create_session(user["id"])
    return {
        "token": token,
        "expiresAt": expires_at.isoformat(),
        "user": user,
    }


def is_development():
    return config.is_development()


def smtp_settings():
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587") or "587"),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from": os.environ.get("SMTP_FROM", "").strip() or os.environ.get("SMTP_USER", "").strip(),
        "tls": os.environ.get("SMTP_TLS", "true").strip().lower() not in {"0", "false", "no"},
    }


def email_sender():
    return os.environ.get("EMAIL_FROM", "").strip() or os.environ.get("SMTP_FROM", "").strip() or os.environ.get("SMTP_USER", "").strip()


def resend_settings():
    return {
        "api_key": os.environ.get("RESEND_API_KEY", "").strip(),
        "from": email_sender(),
    }


def build_otp_message(email, otp):
    message = EmailMessage()
    message["Subject"] = "Kode Verifikasi JobFit"
    message["From"] = email_sender()
    message["To"] = email
    message.set_content(
        "Kode verifikasi JobFit Anda adalah:\n\n"
        f"{otp}\n\n"
        "Kode ini berlaku selama 10 menit. Abaikan email ini jika Anda tidak membuat akun JobFit."
    )
    message.add_alternative(build_otp_html(otp), subtype="html")
    return message


def build_otp_html(otp):
    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,sans-serif;color:#111827;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f7fb;padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:28px 28px 10px;">
                <h1 style="margin:0;font-size:24px;line-height:1.3;color:#111827;">Kode Verifikasi JobFit</h1>
                <p style="margin:12px 0 0;font-size:15px;line-height:1.6;color:#4b5563;">
                  Gunakan kode berikut untuk menyelesaikan pendaftaran akun JobFit Anda.
                </p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:18px 28px;">
                <div style="display:inline-block;padding:16px 28px;border-radius:14px;background:#eef2ff;color:#1e3a8a;font-size:34px;font-weight:800;letter-spacing:6px;">
                  {otp}
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 28px 28px;">
                <p style="margin:0;font-size:14px;line-height:1.6;color:#4b5563;">
                  Kode ini berlaku selama <strong>10 menit</strong>. Jika Anda tidak membuat akun JobFit, abaikan email ini.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_otp_email_resend(email, otp):
    settings = resend_settings()
    if not settings["api_key"] or not settings["from"]:
        raise RuntimeError("Resend belum dikonfigurasi.")

    payload = {
        "from": settings["from"],
        "to": [email],
        "subject": "Kode Verifikasi JobFit",
        "text": (
            "Kode verifikasi JobFit Anda adalah:\n\n"
            f"{otp}\n\n"
            "Kode ini berlaku selama 10 menit. Abaikan email ini jika Anda tidak membuat akun JobFit."
        ),
        "html": build_otp_html(otp),
    }
    data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=15) as response:
            if response.status >= 300:
                raise RuntimeError(f"Resend gagal mengirim email: HTTP {response.status}")
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend gagal mengirim email: HTTP {error.code} {body}") from error


def send_otp_email(email, otp):
    if os.environ.get("RESEND_API_KEY", "").strip():
        send_otp_email_resend(email, otp)
        return

    settings = smtp_settings()
    if not settings["host"] or not settings["from"]:
        raise RuntimeError("SMTP belum dikonfigurasi.")

    message = build_otp_message(email, otp)

    with smtplib.SMTP(settings["host"], settings["port"], timeout=15) as smtp:
        if settings["tls"]:
            smtp.starttls()
        if settings["user"] and settings["password"]:
            smtp.login(settings["user"], settings["password"])
        smtp.send_message(message)


def build_otp_response(otp_payload, otp_sent):
    response = {
        "verificationId": otp_payload["verificationId"],
        "email": otp_payload["email"],
        "expiresAt": otp_payload["expiresAt"],
        "otpSent": otp_sent,
    }
    if is_development() and not otp_sent:
        response["devOtp"] = otp_payload["otp"]
    return response


def issue_register_otp(user):
    otp_payload = database.create_email_otp(user["id"], user["email"])
    try:
        send_otp_email(otp_payload["email"], otp_payload["otp"])
        return build_otp_response(otp_payload, True)
    except Exception as error:
        if is_development():
            logger.warning("OTP email delivery failed; using development fallback: %s", error)
            return build_otp_response(otp_payload, False)
        logger.exception("OTP email delivery failed.")
        raise HTTPException(status_code=500, detail="Email OTP tidak terkirim. Coba beberapa saat lagi.") from error
