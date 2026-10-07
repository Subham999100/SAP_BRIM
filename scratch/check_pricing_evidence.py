import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"c:\Users\Subham Patnaik\OneDrive\Desktop\agent\SAP_Project")

from backend.app.database import SessionLocal
from backend.app.models.chunk import DocumentChunk

db = SessionLocal()

concepts = {
    "A. Recurring subscription charge": ["recurring", "subscription", "monthly price", "billing plan"],
    "B. Included/free quantity / allowance": ["allowance", "included quantity", "free units", "quota"],
    "C. Usage charging": ["usage", "metering", "chargeable event", "consumption"],
    "D. Time/day-based pricing": ["weekday", "weekend", "calendar", "time-based", "day-based"],
    "E. Promotional/discount period": ["discount", "promotional", "validity period", "first months"],
    "F. Price Plans / Rate Plans": ["price plan", "charge plan", "rate plan"],
    "G. Price Tables": ["price table", "mapping table", "range table", "graduated scale"],
    "H. Testing/debugging": ["test", "debug", "prototype"],
    "I. Business validation": ["validation", "verification", "audit"]
}

try:
    for cat, terms in concepts.items():
        print(f"\n==========================================")
        print(f"{cat}")
        print(f"==========================================")
        for term in terms:
            matches = db.query(DocumentChunk).filter(DocumentChunk.chunk_text.ilike(f"%{term}%")).all()
            print(f"Term '{term}': {len(matches)} matches")
            # Show top 2 docs/pages
            doc_counts = {}
            for m in matches:
                doc_counts[m.document_name] = doc_counts.get(m.document_name, 0) + 1
            print(f"   Distribution: {doc_counts}")
            if matches:
                first = matches[0]
                print(f"   Sample [{first.document_name} P.{first.page_number}]: {first.chunk_text[:160].strip()}...")
finally:
    db.close()
