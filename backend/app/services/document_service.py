import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import pymupdf

class DocumentService:
    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def extract_pdf_pages(file_path: Path) -> List[Dict[str, Any]]:
        """
        Extracts text from each page using PyMuPDF.
        Returns list of dicts: {'page_number': int, 'text': str, 'section_headings': list}
        """
        pages_data = []
        doc = pymupdf.open(str(file_path))
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_number = page_idx + 1
                text = page.get_text("text")

                # Detect potential section headings
                headings = []
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                for line in lines:
                    if re.match(r"^(Section\s+\d+|Chapter\s+\d+|\d+\.\d+|\b[A-Z0-9\s\-_]{3,40}\b)", line) and len(line) < 60:
                        headings.append(line)

                cleaned_text = DocumentService.clean_text(text)
                pages_data.append({
                    "page_number": page_number,
                    "text": cleaned_text,
                    "headings": headings
                })
        finally:
            doc.close()

        return pages_data

    @staticmethod
    def clean_text(text: str) -> str:
        # Normalize newlines and excess whitespace
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove repetitive header/footer page markers like "Page X of Y"
        text = re.sub(r"(?i)Page\s+\d+(\s+of\s+\d+)?", "", text)
        return text.strip()

    @staticmethod
    def chunk_page_text(
        text: str,
        page_number: int,
        document_name: str,
        headings: List[str],
        chunk_size: int = 650,
        chunk_overlap: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Intelligently chunks text with sliding window and heading preservation.
        """
        if not text:
            return []

        # Find primary section heading for this page
        primary_section = headings[0] if headings else f"Page {page_number}"

        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0

        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # If not at the end of the text, try to split at a sentence boundary (. \n)
            if end < text_length:
                break_point = max(
                    text.rfind(". ", start, end),
                    text.rfind(".\n", start, end),
                    text.rfind("\n\n", start, end)
                )
                if break_point != -1 and break_point > start + 200:
                    end = break_point + 1

            chunk_text = text[start:end].strip()
            if len(chunk_text) > 30:  # Ignore trivial snippets
                chunks.append({
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "document_name": document_name,
                    "section": primary_section,
                    "chunk_text": chunk_text,
                    "metadata": {
                        "document": document_name,
                        "page": page_number,
                        "section": primary_section,
                        "char_length": len(chunk_text)
                    }
                })
                chunk_index += 1

            if end >= text_length:
                break
            start = end - chunk_overlap

        return chunks

document_service = DocumentService()
