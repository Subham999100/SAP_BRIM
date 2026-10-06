import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# Ensure backend root is on sys.path if invoked directly
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.config import settings
from backend.app.database import SessionLocal, init_db
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.services.document_service import document_service
from backend.app.services.embedding_service import embedding_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingestion")

def run_ingestion(db: Session = None) -> List[Dict[str, Any]]:
    should_close_db = False
    if db is None:
        init_db()
        db = SessionLocal()
        should_close_db = True

    results = []
    doc_dir = settings.DOCUMENTS_DIR
    if not doc_dir.exists():
        logger.warning(f"Documents directory does not exist: {doc_dir}. Creating it.")
        doc_dir.mkdir(parents=True, exist_ok=True)
        return results

    pdf_files = sorted(list(doc_dir.glob("*.pdf")))
    logger.info(f"Discovered {len(pdf_files)} PDF documents in {doc_dir}")

    for pdf_path in pdf_files:
        filename = pdf_path.name
        file_hash = document_service.compute_file_hash(pdf_path)

        # Idempotency check: check if document already exists with same hash
        existing_doc = db.query(Document).filter(Document.filename == filename).first()
        if existing_doc and existing_doc.file_hash == file_hash:
            logger.info(f"Skipping '{filename}': already ingested with identical checksum.")
            results.append({
                "filename": filename,
                "status": "skipped",
                "reason": "already_up_to_date",
                "chunks": len(existing_doc.chunks)
            })
            continue

        logger.info(f"Processing document: '{filename}' ...")
        pages = document_service.extract_pdf_pages(pdf_path)
        page_count = len(pages)

        # If document already exists with different hash, remove old chunks
        if existing_doc:
            logger.info(f"Updating existing document '{filename}' with new contents.")
            db.query(DocumentChunk).filter(DocumentChunk.document_id == existing_doc.id).delete()
            existing_doc.file_hash = file_hash
            existing_doc.page_count = page_count
            doc_record = existing_doc
        else:
            title = filename.replace(".pdf", "").replace("_", " ")
            doc_record = Document(
                filename=filename,
                title=title,
                file_hash=file_hash,
                version="1.0",
                page_count=page_count
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)

        # Process chunks
        total_chunks = 0
        all_chunk_dicts = []
        for page_data in pages:
            page_num = page_data["page_number"]
            page_text = page_data["text"]
            headings = page_data["headings"]

            chunks = document_service.chunk_page_text(
                text=page_text,
                page_number=page_num,
                document_name=filename,
                headings=headings
            )
            all_chunk_dicts.extend(chunks)

        # Batch embed chunk texts for high performance
        if all_chunk_dicts:
            texts_to_embed = [c["chunk_text"] for c in all_chunk_dicts]
            embeddings = embedding_service.embed_batch(texts_to_embed)

            for i, chunk_data in enumerate(all_chunk_dicts):
                chunk_record = DocumentChunk(
                    document_id=doc_record.id,
                    document_name=filename,
                    chunk_index=i,
                    page_number=chunk_data["page_number"],
                    section=chunk_data["section"],
                    chunk_text=chunk_data["chunk_text"],
                    metadata_json=str(chunk_data["metadata"]),
                    embedding=embeddings[i]
                )
                db.add(chunk_record)
                total_chunks += 1

        db.commit()
        logger.info(f"Successfully ingested '{filename}': {page_count} pages, {total_chunks} chunks.")
        results.append({
            "filename": filename,
            "status": "ingested",
            "page_count": page_count,
            "chunks": total_chunks
        })

    if should_close_db:
        db.close()

    return results

if __name__ == "__main__":
    logger.info("Starting Developer Ingestion Pipeline...")
    res = run_ingestion()
    logger.info(f"Ingestion finished: {res}")
