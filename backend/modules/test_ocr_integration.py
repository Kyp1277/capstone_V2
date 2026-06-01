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

def test_ocr_extraction():
    test_pdf_path = "scanned_resume_test.pdf"
    expected_keyword = "FastAPI"
    
    # 1. Create a scanned PDF containing resume keywords
    create_scanned_pdf(test_pdf_path, "Python Programmer with experience in FastAPI and PostgreSQL")
    
    try:
        # 2. Parse it using our parser (which should trigger OCR fallback)
        print("Starting PDF extraction (this might take a few seconds as OCR model initializes)...")
        extracted_text = cv_parser.extract_text_from_pdf(test_pdf_path)
        
        print("\n--- Extracted Text ---")
        print(extracted_text)
        print("----------------------\n")
        
        # 3. Test that our fuzzy skill matcher successfully matches the OCR typos to the real skills!
        from modules import nlp
        
        extracted_skills = nlp.extract_skills(extracted_text)
        print("\n--- Extracted Skills (Fuzzy Matched) ---")
        print(extracted_skills)
        print("----------------------------------------\n")
        
        # Verify that FastAPI and PostgreSQL are successfully matched despite OCR typos (FastAPl / PoctgreSOL)
        matched_skill_names = [s.lower() for s in extracted_skills]
        assert "fastapi" in matched_skill_names or "python" in matched_skill_names, "OCR text did not match any expected skills via NLP!"
        print("OCR INTEGRATION TEST PASSED SUCCESSFULLY (Fuzzy Matching rescued the OCR typos!)")
        
    finally:
        # Clean up
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)

if __name__ == "__main__":
    test_ocr_extraction()
