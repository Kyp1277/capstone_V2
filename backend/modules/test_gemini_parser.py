import sys
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGES = ROOT.parent / ".codex-python-packages"
if LOCAL_PACKAGES.exists() and str(LOCAL_PACKAGES) not in sys.path:
    sys.path.append(str(LOCAL_PACKAGES))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import types
from unittest.mock import MagicMock, patch

# Mock google generativeai package to allow running tests without installation
try:
    import google.generativeai
except ImportError:
    mock_genai = MagicMock()
    sys.modules["google"] = MagicMock()
    sys.modules["google.generativeai"] = mock_genai

from modules import nlp

class MockGenerativeModel:
    def __init__(self, *args, **kwargs):
        pass

    def generate_content(self, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.text = """
        {
            "skills": ["React", "FastAPI", "Python"],
            "work_experiences": [
                {
                    "role": "Frontend Developer",
                    "years": 2.5,
                    "company": "Dicoding",
                    "duration": "Jan 2021 - Jun 2023"
                }
            ],
            "education": [
                {
                    "degree": "Bachelor",
                    "major": "Computer Science",
                    "institution": "Universitas Indonesia"
                }
            ],
            "summary": "Experienced Frontend Developer specializing in React and FastAPI.",
            "improvements": [
                "Ambil sertifikasi React di Dicoding",
                "Bangun portofolio e-commerce dengan Next.js"
            ]
        }
        """
        return mock_response


mock_genai = types.SimpleNamespace(
    configure=lambda **kwargs: None,
    GenerativeModel=MockGenerativeModel,
    GenerationConfig=lambda **kwargs: kwargs,
)
mock_google = types.SimpleNamespace(generativeai=mock_genai)


@patch.dict(sys.modules, {"google": mock_google, "google.generativeai": mock_genai})
@patch.dict(os.environ, {"GEMINI_API_KEY": "fake-api-key", "JOBFIT_ENABLE_GEMINI": "true"})
def test_gemini_parser_successful():
    text = "Some random resume text"
    result = nlp.extract_profile_with_gemini(text, target_role="Frontend Developer")
    
    assert result is not None
    assert "React" in result["skills"]
    assert len(result["work_experiences"]) == 1
    assert result["work_experiences"][0]["role"] == "Frontend Developer"
    assert result["education"][0]["degree"] == "Bachelor"
    assert "Computer Science" in result["education"][0]["major"]
    assert result["summary"] == "Experienced Frontend Developer specializing in React and FastAPI."
    assert "improvements" in result
    assert "Ambil sertifikasi React di Dicoding" in result["improvements"]
    print("test_gemini_parser_successful: PASSED")

@patch.dict(os.environ, {}, clear=True)
def test_gemini_parser_fallback_on_no_key():
    text = "Some random resume text"
    # Should return None when there is no API Key, triggering fallback
    result = nlp.extract_profile_with_gemini(text)
    assert result is None
    print("test_gemini_parser_fallback_on_no_key: PASSED")

if __name__ == "__main__":
    test_gemini_parser_successful()
    test_gemini_parser_fallback_on_no_key()
    print("ALL GEMINI PARSER MOCK TESTS PASSED SUCCESSFULLY!")
