import os
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
LOCAL_PACKAGES = PROJECT_ROOT / ".codex-python-packages"
if LOCAL_PACKAGES.exists() and str(LOCAL_PACKAGES) not in sys.path:
    sys.path.append(str(LOCAL_PACKAGES))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules import auth_service, config  # noqa: E402


@contextmanager
def temporary_env(values):
    old_values = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_production_otp_response_never_exposes_dev_otp():
    payload = {
        "verificationId": "verify-1",
        "email": "user@example.com",
        "expiresAt": "2026-06-01T00:00:00+00:00",
        "otp": "123456",
    }

    with temporary_env({"APP_ENV": "production"}):
        response = auth_service.build_otp_response(payload, False)
        assert "devOtp" not in response

    with temporary_env({"APP_ENV": "development"}):
        response = auth_service.build_otp_response(payload, False)
        assert response["devOtp"] == "123456"


def test_production_config_requires_database_and_smtp():
    with temporary_env(
        {
            "APP_ENV": "production",
            "DATABASE_URL": "",
            "POSTGRES_URL": "",
            "SMTP_HOST": "",
            "SMTP_FROM": "",
            "SMTP_USER": "",
            "SMTP_PASSWORD": "",
            "FRONTEND_ORIGINS": "",
        }
    ):
        try:
            config.validate_production_config()
        except RuntimeError as error:
            message = str(error)
            assert "DATABASE_URL" in message
            assert "SMTP_HOST" in message
        else:
            raise AssertionError("Expected production config validation to fail")


def test_production_config_rejects_wildcard_cors_origin():
    base_env = {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/jobfit",
        "POSTGRES_URL": "",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_FROM": "noreply@example.com",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
    }

    with temporary_env({**base_env, "FRONTEND_ORIGINS": "*"}):
        errors = config.production_config_errors()
        assert any("wildcard" in error.lower() for error in errors)

    with temporary_env({**base_env, "FRONTEND_ORIGINS": ""}):
        assert config.production_config_errors() == []


def test_cors_origin_defaults_are_hosting_safe():
    with temporary_env({"APP_ENV": "production", "FRONTEND_ORIGINS": "https://app.example.com, https://www.example.com/"}):
        assert config.cors_origins() == ["https://app.example.com", "https://www.example.com"]

    with temporary_env({"APP_ENV": "production", "FRONTEND_ORIGINS": ""}):
        assert config.cors_origins() == []

    with temporary_env({"APP_ENV": "development", "FRONTEND_ORIGINS": ""}):
        assert config.cors_origins() == ["*"]


def run_all():
    tests = [
        test_production_otp_response_never_exposes_dev_otp,
        test_production_config_requires_database_and_smtp,
        test_production_config_rejects_wildcard_cors_origin,
        test_cors_origin_defaults_are_hosting_safe,
    ]

    for test in tests:
        test()
        print(f"OK {test.__name__}")

    print("SECURITY HARDENING TESTS PASSED")


if __name__ == "__main__":
    run_all()
