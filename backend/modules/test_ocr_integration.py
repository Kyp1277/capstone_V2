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
from PIL import Image, ImageDraw
from modules import cv_parser

def create_scanned_pdf(output_path, text_content):
    """Dynamically creates a scanned (image-only) PDF containing specified text."""
    # Create a blank image with white background
    img = Image.new('RGB', (800, 400), color='white')
    d = ImageDraw.Draw(img)
    # Write some simple text
    d.text((50, 100), text_content, fill='black')
    # Save the image as PDF
    img.save(output_path, "PDF", resolution=100.0)
    print(f"Created scanned PDF at {output_path}")

from unittest.mock import patch

@patch("modules.cv_parser._attempt_ocr")
def test_ocr_fallback_uses_mocked_text_for_skill_extraction(mock_attempt_ocr):
    mock_attempt_ocr.return_value = "Python Programmer with experience in FastAPI and PostgreSQL"
    test_pdf_path = "scanned_resume_test.pdf"
    
    # 1. Create a scanned PDF containing resume keywords
    create_scanned_pdf(test_pdf_path, "Python Programmer with experience in FastAPI and PostgreSQL")
    
    try:
        # 2. Parse it using our parser. OCR itself is mocked so this test stays
        # deterministic on machines without Tesseract or OCR system packages.
        extracted_text = cv_parser.extract_text_from_pdf(test_pdf_path)
        
        print("\n--- Extracted Text ---")
        print(extracted_text)
        print("----------------------\n")
        
        # 3. Test that the fallback OCR text feeds the skill matcher.
        from modules import nlp
        
        extracted_skills = nlp.extract_skills(extracted_text)
        print("\n--- Extracted Skills (Fuzzy Matched) ---")
        print(extracted_skills)
        print("----------------------------------------\n")
        
        matched_skill_names = [s.lower() for s in extracted_skills]
        assert "fastapi" in matched_skill_names or "python" in matched_skill_names, "OCR text did not match any expected skills via NLP!"
        print("OCR FALLBACK MOCK TEST PASSED SUCCESSFULLY")
        
    finally:
        # Clean up
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)

if __name__ == "__main__":
    test_ocr_fallback_uses_mocked_text_for_skill_extraction()
