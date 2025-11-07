# server/tools/ocr_tool.py
import pdfplumber
import pytesseract
from PIL import Image
from typing import Dict
from server.config import MAX_OCR_PAGES


def pdf_to_text(path: str, max_pages: int = MAX_OCR_PAGES) -> Dict:
    texts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= max_pages:
                break
            try:
                text = page.extract_text()
                if not text:
                    im = page.to_image(resolution=200).original
                    text = pytesseract.image_to_string(im)
                texts.append({"page": i + 1, "text": text or ""})
            except Exception as e:
                texts.append({"page": i + 1, "error": str(e)})
    return {"pages": texts}


def image_to_text(image_path: str) -> Dict:
    return {"text": pytesseract.image_to_string(Image.open(image_path))}
