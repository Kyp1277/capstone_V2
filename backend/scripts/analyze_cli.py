import argparse
import contextlib
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from modules.analysis_service import analyze_cv_file  # noqa: E402


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run JobFit CV analysis and return JSON.")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--target-role", default="")
    parser.add_argument("--analysis-mode", default="targeted")
    args = parser.parse_args()

    with contextlib.redirect_stdout(sys.stderr):
        result = analyze_cv_file(args.pdf, args.target_role, args.analysis_mode)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
