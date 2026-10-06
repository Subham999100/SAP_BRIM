import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf

class DocumentService:
    SAP_DOC_METADATA = {
        "pdfdownload.pdf": {
            "title": "SAP S/4HANA Subscription Order Management (SOM) Guide",
            "module": "SOM / BRIM",
            "product": "SAP S/4HANA BRIM"
        },
        "SAP CC.pdf": {
            "title": "SAP Convergent Charging (CC) Implementation Guide",
            "module": "CC / BRIM",
            "product": "SAP Convergent Charging"
        },
        "SAP CI1.pdf": {
            "title": "SAP Cloud Integration & Convergent Invoicing Guide (Part 1)",
            "module": "CI / BRIM",
            "product": "SAP Convergent Invoicing"
        },
        "SAP CI2.pdf": {
            "title": "SAP Cloud Integration & Convergent Invoicing Guide (Part 2)",
            "module": "CI / BRIM",
            "product": "SAP Convergent Invoicing"
        },
        "SAP CI3.pdf": {
            "title": "SAP Cloud Integration & Convergent Invoicing Guide (Part 3)",
            "module": "CI / BRIM",
            "product": "SAP Convergent Invoicing"
        },
        "SAP CI4.pdf": {
            "title": "SAP Cloud Integration & Convergent Invoicing Guide (Part 4)",
            "module": "CI / BRIM",
            "product": "SAP Convergent Invoicing"
        },
        "SAP FI-CA.pdf": {
            "title": "SAP Contract Accounts Receivable and Payable (FI-CA) Guide",
            "module": "FI-CA / BRIM",
            "product": "SAP FI-CA"
        }
    }

    @staticmethod
    def get_document_info(filename: str) -> Dict[str, str]:
        if filename in DocumentService.SAP_DOC_METADATA:
            return DocumentService.SAP_DOC_METADATA[filename]
        clean_title = filename.replace(".pdf", "").replace("_", " ")
        return {
            "title": clean_title,
            "module": "General SAP",
            "product": "SAP ERP"
        }

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        # Filter private-use unicode glyphs and replacement chars
        text = re.sub(r"[\ue000-\uf8ff\ufffd]", " ", text)
        # Remove repetitive SAP Help Portal headers & footers
        text = re.sub(r"Warning\s+This document has been generated from SAP Help Portal[^\n]*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"Original content:\s*https?://help\.sap\.com[^\n]*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"Generated on:\s*\d{4}-\d{2}-\d{2}[^\n]*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"(?i)Page\s+\d+(\s+of\s+\d+)?", "", text)
        text = re.sub(r"(?i)SAP S/4HANA\s*\|\s*\d{4}[^\n]*", "", text)
        # Normalize newlines and excess whitespace
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def extract_pdf_pages(file_path: Path) -> List[Dict[str, Any]]:
        """
        Extracts text and section structure from each page using PyMuPDF.
        Tracks active section hierarchy across pages.
        """
        pages_data = []
        doc = pymupdf.open(str(file_path))
        active_section = "Overview"

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_number = page_idx + 1
                raw_text = page.get_text("text") or ""
                cleaned_text = DocumentService.clean_text(raw_text)

                # Detect potential section headings
                headings = []
                lines = [l.strip() for l in cleaned_text.split("\n") if l.strip()]
                for line in lines:
                    # Match numbered sections (e.g. "1.1 Flexible Billing", "Chapter 2", "Section 3.4")
                    # or uppercase short topic titles
                    if (
                        re.match(r"^(?:(?:Section|Chapter)\s+\d+(?:\.\d+)*|\d+(?:\.\d+)+\s+[A-Z0-9].*|\d+\s+[A-Z][A-Za-z0-9\s\-_/:]{3,40})$", line)
                        and len(line) < 70
                    ):
                        headings.append(line)
                    elif len(line) < 45 and line.isupper() and not line.startswith("PAGE"):
                        headings.append(line.title())

                if headings:
                    active_section = headings[0]

                pages_data.append({
                    "page_number": page_number,
                    "text": cleaned_text,
                    "headings": headings,
                    "active_section": active_section
                })
        finally:
            doc.close()

        return pages_data

    @staticmethod
    def chunk_page_text(
        text: str,
        page_number: int,
        document_name: str,
        active_section: str,
        target_chunk_size: int = 1200,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Structure-aware chunker designed for SAP enterprise documentation:
        - Targets 1,000-1,400 chars.
        - Preserves numbered procedures (1. 2. Step X), tables, and notes.
        - Splits on logical paragraph/procedure breaks rather than cutting sentences.
        """
        if not text or len(text.strip()) < 30:
            return []

        cleaned = text.strip()
        doc_info = DocumentService.get_document_info(document_name)

        # Detect structural features
        has_procedure = bool(re.search(r"(?:Step\s+\d+|\bProcedure\b|\bPrerequisites\b|\n\s*\d+\.\s+[A-Z])", cleaned, re.IGNORECASE))
        has_table = bool(re.search(r"(?:\||\bTable\b|\bField\b.*\bDescription\b)", cleaned, re.IGNORECASE))

        # If page text is within standard chunk size range, keep as a single unified chunk
        if len(cleaned) <= target_chunk_size + 300:
            return [{
                "chunk_index": 0,
                "page_number": page_number,
                "document_name": document_name,
                "section": active_section,
                "chunk_text": cleaned,
                "metadata": {
                    "document": document_name,
                    "title": doc_info["title"],
                    "module": doc_info["module"],
                    "product": doc_info["product"],
                    "page": page_number,
                    "section": active_section,
                    "char_length": len(cleaned),
                    "has_procedure": has_procedure,
                    "has_table": has_table
                }
            }]

        chunks = []
        start = 0
        text_length = len(cleaned)
        chunk_idx = 0

        while start < text_length:
            end = min(start + target_chunk_size, text_length)

            # If not at the end of the text, seek a clean logical boundary
            if end < text_length:
                # 1. Paragraph boundary
                p_break = cleaned.rfind("\n\n", start + 300, end)
                if p_break != -1:
                    end = p_break
                else:
                    # 2. Numbered step boundary (e.g. "\n1. ", "\n2. ")
                    step_match = None
                    for m in re.finditer(r"\n(?:\d+\.|\-|\*)\s+", cleaned[start + 300 : end]):
                        step_match = start + 300 + m.start()
                    if step_match:
                        end = step_match
                    else:
                        # 3. Sentence boundary (". ", ".\n")
                        sent_break = max(
                            cleaned.rfind(". ", start + 300, end),
                            cleaned.rfind(".\n", start + 300, end)
                        )
                        if sent_break != -1:
                            end = sent_break + 1
                        else:
                            # 4. Line break
                            line_break = cleaned.rfind("\n", start + 300, end)
                            if line_break != -1:
                                end = line_break

            chunk_content = cleaned[start:end].strip()
            if len(chunk_content) >= 60:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "page_number": page_number,
                    "document_name": document_name,
                    "section": active_section,
                    "chunk_text": chunk_content,
                    "metadata": {
                        "document": document_name,
                        "title": doc_info["title"],
                        "module": doc_info["module"],
                        "product": doc_info["product"],
                        "page": page_number,
                        "section": active_section,
                        "char_length": len(chunk_content),
                        "has_procedure": has_procedure,
                        "has_table": has_table
                    }
                })
                chunk_idx += 1

            if end >= text_length:
                break
            start = max(end - chunk_overlap, start + 100)

        return chunks

document_service = DocumentService()

