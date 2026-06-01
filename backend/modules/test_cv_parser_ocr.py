from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGES = ROOT.parent / ".codex-python-packages"
if LOCAL_PACKAGES.exists() and str(LOCAL_PACKAGES) not in sys.path:
    sys.path.append(str(LOCAL_PACKAGES))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules import cv_parser


class FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakePdf:
    def __init__(self, page_texts):
        self.pages = [FakePage(text) for text in page_texts]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class MonkeyPatch:
    def __init__(self):
        self._items = []

    def set(self, obj, name, value):
        self._items.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def restore(self):
        for obj, name, value in reversed(self._items):
            setattr(obj, name, value)


def test_text_pdf_skips_ocr():
    patch = MonkeyPatch()
    calls = []
    long_text = "Python FastAPI PostgreSQL " * 8

    try:
        patch.set(cv_parser.pdfplumber, "open", lambda _path: FakePdf([long_text]))
        patch.set(cv_parser, "_attempt_ocr", lambda _path: calls.append(_path) or "OCR TEXT")

        assert cv_parser.extract_text_from_pdf("text.pdf").strip() == long_text.strip()
        assert calls == []
    finally:
        patch.restore()


def test_short_text_pdf_uses_ocr_when_available():
    patch = MonkeyPatch()

    try:
        patch.set(cv_parser.pdfplumber, "open", lambda _path: FakePdf([""]))
        patch.set(cv_parser, "_attempt_ocr", lambda _path: "OCR extracted CV text")

        assert cv_parser.extract_text_from_pdf("scan.pdf") == "OCR extracted CV text"
    finally:
        patch.restore()


def test_short_text_pdf_stays_safe_when_ocr_unavailable():
    patch = MonkeyPatch()

    try:
        patch.set(cv_parser.pdfplumber, "open", lambda _path: FakePdf(["short"]))
        patch.set(cv_parser, "_attempt_ocr", lambda _path: "")

        assert cv_parser.extract_text_from_pdf("scan.pdf").strip() == "short"
    finally:
        patch.restore()


if __name__ == "__main__":
    test_text_pdf_skips_ocr()
    test_short_text_pdf_uses_ocr_when_available()
    test_short_text_pdf_stays_safe_when_ocr_unavailable()
    print("CV PARSER OCR TESTS PASSED")
