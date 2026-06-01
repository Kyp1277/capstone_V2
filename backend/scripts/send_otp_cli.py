import argparse
import contextlib
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from modules.auth_service import send_otp_email  # noqa: E402


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Send JobFit OTP email via Python SMTP helper.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--otp", required=True)
    args = parser.parse_args()

    with contextlib.redirect_stdout(sys.stderr):
        send_otp_email(args.email, args.otp)

    print("OK")


if __name__ == "__main__":
    main()
