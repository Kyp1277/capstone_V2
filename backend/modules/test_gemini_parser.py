import os
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules import nlp  # noqa: E402


@patch.dict(os.environ, {"GEMINI_API_KEY": "fake-api-key", "JOBFIT_ENABLE_GEMINI": "true"})
def test_external_parser_remains_disabled_even_if_env_is_set():
    result = nlp.extract_profile_with_gemini("Some random resume text", target_role="Frontend Developer")
    assert result is None
    print("test_external_parser_remains_disabled_even_if_env_is_set: PASSED")


@patch.dict(os.environ, {}, clear=True)
def test_external_parser_fallback_without_key():
    result = nlp.extract_profile_with_gemini("Some random resume text")
    assert result is None
    print("test_external_parser_fallback_without_key: PASSED")


if __name__ == "__main__":
    test_external_parser_remains_disabled_even_if_env_is_set()
    test_external_parser_fallback_without_key()
    print("EXTERNAL PARSER DISABLED TESTS PASSED")
