import logging
import os
import re

import pdfplumber


logger = logging.getLogger(__name__)

# Minimum character threshold to consider pdfplumber extraction successful.
# If extracted text is below this, OCR fallback is attempted.
_MIN_TEXT_LENGTH = int(os.environ.get("MIN_EXTRACTED_TEXT_LENGTH", "80"))


# =========================================
# OCR FALLBACK
# =========================================
# K4: If pdfplumber returns too little text (scanned PDF), try OCR.
# Requires either pytesseract+Pillow or easyocr to be installed.
# Gracefully degrades if neither is available.

def _ocr_with_pytesseract(pdf_path):
    """Extract text from scanned PDF using pytesseract (tesseract-ocr)."""
    try:
        import pytesseract
        from PIL import Image
        import pdfplumber
    except ImportError:
        return None

    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Render page as image at 200 DPI
                img = page.to_image(resolution=200).original
                page_text = pytesseract.image_to_string(img, lang="ind+eng")
                if page_text:
                    text_parts.append(page_text)
        result = "\n".join(text_parts).strip()
        if result:
            logger.info("pytesseract OCR extracted %d chars from %s", len(result), pdf_path)
        return result or None
    except Exception:
        logger.exception("pytesseract OCR failed for: %s", pdf_path)
        return None


def _ocr_with_easyocr(pdf_path):
    """Extract text from scanned PDF using easyocr."""
    try:
        import easyocr
        import pdfplumber
        import numpy as np
    except ImportError:
        return None

    try:
        reader = easyocr.Reader(["id", "en"], gpu=False, verbose=False)
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=200).original
                img_array = np.array(img)
                results = reader.readtext(img_array, detail=0, paragraph=True)
                if results:
                    text_parts.append("\n".join(results))
        result = "\n".join(text_parts).strip()
        if result:
            logger.info("easyocr OCR extracted %d chars from %s", len(result), pdf_path)
        return result or None
    except Exception:
        logger.exception("easyocr OCR failed for: %s", pdf_path)
        return None


def _attempt_ocr(pdf_path):
    """
    Try available OCR engines in order: pytesseract first, then easyocr.
    Returns extracted text or empty string if all fail or none installed.
    """
    # Try pytesseract first (lighter dependency)
    result = _ocr_with_pytesseract(pdf_path)
    if result:
        return result

    # Fallback to easyocr
    result = _ocr_with_easyocr(pdf_path)
    if result:
        return result

    logger.warning(
        "OCR fallback unavailable for %s. "
        "Install pytesseract (pip install pytesseract Pillow) or "
        "easyocr (pip install easyocr) to enable scanned PDF support.",
        pdf_path,
    )
    return ""


# =========================================
# MAIN EXTRACTION
# =========================================

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.

    Strategy:
    1. Try pdfplumber (fast, works for text-layer PDFs).
    2. If result is below MIN_EXTRACTED_TEXT_LENGTH threshold, attempt OCR
       so that scanned/image-based CVs are not silently discarded (K4).
    """
    text = ""

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        logger.exception("pdfplumber failed to read PDF: %s", pdf_path)

    # K4: If pdfplumber returned almost nothing, the PDF is likely scanned.
    # Attempt OCR as a fallback before giving up.
    if len(text.strip()) < _MIN_TEXT_LENGTH:
        logger.info(
            "pdfplumber returned only %d chars (threshold %d); attempting OCR for %s",
            len(text.strip()),
            _MIN_TEXT_LENGTH,
            pdf_path,
        )
        ocr_text = _attempt_ocr(pdf_path)
        if ocr_text:
            text = ocr_text

    return text
