import io
import os

import docx
import fitz
import pytesseract
from PIL import Image

MIN_TEXT_LENGTH_THRESHOLD = 50


def extract_text_from_docx(file_path: str) -> str | None:
    """Extract text from a DOCX document."""
    if not os.path.exists(file_path):
        print(f"Error: DOCX file not found at {file_path}")
        return None

    try:
        document = docx.Document(file_path)
        text = "\n".join(
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )
        print(f"python-docx extracted {len(text)} characters.")
        return text or None
    except Exception as e:
        print(f"Error reading DOCX file {file_path}: {e}")
        return None


def extract_text_from_pdf(file_path: str) -> str | None:
    """Extract normal text from a PDF file using PyMuPDF."""
    if not os.path.exists(file_path):
        print(f"Error: PDF file not found at {file_path}")
        return None

    try:
        pdf_document = fitz.open(file_path)
        text_parts = []

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_text = page.get_text("text")
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())

        pdf_document.close()
        text = "\n\n".join(text_parts)
        print(f"PyMuPDF extracted {len(text)} characters from PDF.")
        return text or None
    except Exception as e:
        print(f"Error reading PDF file {file_path}: {e}")
        return None


def ocr_pdf(file_path: str, language: str = "eng") -> str | None:
    """OCR a scanned PDF by converting each page to an image and extracting text."""
    if not os.path.exists(file_path):
        print(f"Error: PDF file not found for OCR at {file_path}")
        return None

    print(f"Attempting OCR on {file_path}...")
    text_parts = []

    try:
        pdf_document = fitz.open(file_path)

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))

            try:
                page_text = pytesseract.image_to_string(image, lang=language)
                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())
            except pytesseract.TesseractNotFoundError:
                print("\n--- Tesseract OCR Error ---")
                print("Tesseract executable not found. Please ensure Tesseract is installed and in PATH.")
                print("__________________________\n")
                pdf_document.close()
                return None
            except Exception as ocr_error:
                print(f"Error during OCR processing on page {page_num + 1}: {ocr_error}")

        pdf_document.close()
        text = "\n\n".join(text_parts)
        print(f"OCR extraction finished, total characters: {len(text)}")
        return text or None
    except Exception as e:
        print(f"Error opening PDF for OCR {file_path}: {e}")
        return None


def parse_resume(file_path: str) -> str | None:
    """Parse a resume from PDF or DOCX, with OCR fallback for scanned PDFs."""
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    _, file_extension = os.path.splitext(file_path)
    text = None

    if file_extension.lower() == ".pdf":
        text = extract_text_from_pdf(file_path)

        if not text or len(text.strip()) < MIN_TEXT_LENGTH_THRESHOLD:
            print(
                f"Initial PDF text extraction yielded minimal text ({len(text or '')} chars). Falling back to OCR."
            )
            text_ocr = ocr_pdf(file_path)

            if text_ocr and len(text_ocr.strip()) > len(text.strip() if text else ""):
                print("Using OCR result because it is more complete.")
                text = text_ocr
            elif text_ocr:
                print("OCR result was not used because the initial extraction was longer.")
            else:
                print("OCR attempt failed or returned no text.")

    elif file_extension.lower() == ".docx":
        text = extract_text_from_docx(file_path)
    else:
        print(f"Error: Unsupported file type '{file_extension}'. Please use PDF or DOCX.")
        return None

    if text and len(text.strip()) > 0:
        print(f"Resume parsed successfully. Total characters: {len(text)}")
        text = '\n'.join(line.strip() for  line in text.splitlines() if line.strip())     
        return text
    else:
        print("Failed to extract meaningful text from the resume after all attempts.")
        return None
    

