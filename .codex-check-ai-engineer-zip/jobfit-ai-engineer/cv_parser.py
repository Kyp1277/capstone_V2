import pdfplumber
import re

# =========================================
# CLEAN TEXT
# =========================================
def clean_text(text):

    if not isinstance(text, str):
        return ""

    # hapus spasi berlebih
    text = re.sub(r"\s+", " ", text)

    return text.strip()

# =========================================
# PDF TEXT EXTRACTOR
# =========================================
def extract_text_from_pdf(pdf_path):

    full_text = ""

    try:

        with pdfplumber.open(pdf_path) as pdf:

            # =====================================
            # LOOP SEMUA HALAMAN
            # =====================================
            for page in pdf.pages:

                try:

                    page_text = page.extract_text()

                    # =================================
                    # VALIDASI TEXT
                    # =================================
                    if page_text and page_text.strip():

                        full_text += page_text + "\n"

                except Exception as page_error:

                    print(
                        f"Error membaca halaman PDF: {page_error}"
                    )

        # =====================================
        # CLEAN TEXT
        # =====================================
        full_text = clean_text(full_text)

        # =====================================
        # DETEKSI PDF SCAN / GAMBAR
        # =====================================
        if len(full_text) < 20:

            return """
            PDF tidak mengandung teks yang dapat dibaca.
            Kemungkinan file berupa hasil scan/gambar.
            Gunakan OCR atau export PDF berbasis text.
            """

        return full_text

    except Exception as e:

        print(f"Error reading PDF: {e}")

        return ""