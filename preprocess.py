# preprocess.py
import os
from pathlib import Path
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract

BOOKS_DIR = Path("data/books")
POPPLER_PATH = None  # Windowsda agar kerak bo'lsa to'ldiring, masalan r"C:\poppler\Library\bin"

def extract_pages_text(pdf_path: Path):
    pages_text = {}
    try:
        reader = PdfReader(str(pdf_path))
        for i, page in enumerate(reader.pages, start=1):
            txt = page.extract_text() or ""
            pages_text[i] = txt.strip()
    except Exception:
        pages_text = {}

    # Agar juda ko'p bo'sh sahifa bo'lsa -> OCR
    empty = sum(1 for t in pages_text.values() if not t)
    if not pages_text or empty / max(1, len(pages_text)) > 0.5:
        images = convert_from_path(str(pdf_path), dpi=200, poppler_path=POPPLER_PATH)
        pages_text = {}
        for i, img in enumerate(images, start=1):
            txt = pytesseract.image_to_string(img, lang='uz+eng')
            pages_text[i] = txt.strip()
    return pages_text

def save_pages(book_id: str, pages_text: dict):
    dest = BOOKS_DIR / book_id / "pages"
    if dest.exists():
        # agar yangilash istasang shu yerda tozalash mumkin
        pass
    dest.mkdir(parents=True, exist_ok=True)
    for p, t in pages_text.items():
        (dest / f"{p}.txt").write_text(t, encoding="utf-8")

if __name__ == "__main__":
    # avtomatik barcha pdflarni olish
    for pdf in BOOKS_DIR.glob("*.pdf"):
        book_id = pdf.stem
        print(f"Processing {pdf} -> book_id={book_id}")
        pages = extract_pages_text(pdf)
        save_pages(book_id, pages)
        print(f"Saved {len(pages)} pages to data/books/{book_id}/pages/")
