from backend.app.database import SessionLocal
from sqlalchemy import text
import re

db = SessionLocal()

query = "Design a 499 telecom pricing plan with 100 GB included data, 10 per additional GB, weekday weekend pricing differences, and a 20 discount for the first 3 months."

def run_lexical(q_str, limit=10):
    # Try strict plainto_tsquery first
    sql_strict = """
    SELECT id, document_name, ts_rank_cd(to_tsvector('english', chunk_text), plainto_tsquery('english', :q)) as score
    FROM document_chunks
    WHERE to_tsvector('english', chunk_text) @@ plainto_tsquery('english', :q)
    ORDER BY score DESC LIMIT :lim;
    """
    rows = db.execute(text(sql_strict), {"q": q_str, "lim": limit}).fetchall()
    if len(rows) >= 5:
        return "strict", rows

    # Fallback to key terms OR-query
    stop_words = {
        "what", "is", "the", "a", "an", "how", "to", "in", "of", "and", "for",
        "with", "does", "do", "explain", "describe", "can", "you", "tell", "me",
        "about", "design", "first", "per", "and", "or", "as", "at", "by", "from",
        "this", "that", "these", "those", "have", "has", "had"
    }
    # Clean tokens, preserve SAP codes and acronyms
    raw_tokens = re.findall(r"\b[a-zA-Z0-9\-_/]+\b", q_str.lower())
    valid_tokens = [t.replace("-", "").replace("/", "") for t in raw_tokens if t not in stop_words and len(t) > 2]
    # Keep up to top 8 distinctive tokens
    if not valid_tokens:
        return "none", []

    or_expr = " | ".join(valid_tokens[:8])
    sql_or = """
    SELECT id, document_name, ts_rank_cd(to_tsvector('english', chunk_text), to_tsquery('english', :q)) as score
    FROM document_chunks
    WHERE to_tsvector('english', chunk_text) @@ to_tsquery('english', :q)
    ORDER BY score DESC LIMIT :lim;
    """
    try:
        rows_or = db.execute(text(sql_or), {"q": or_expr, "lim": limit}).fetchall()
        return f"or ({or_expr})", rows_or
    except Exception as e:
        return f"error: {e}", []

method, hits = run_lexical(query)
print("Method:", method)
print("Number of hits:", len(hits))
for h in hits[:5]:
    print(h)

q2 = "What is a Price Plan in SAP Convergent Charging?"
method2, hits2 = run_lexical(q2)
print("\nMethod 2:", method2)
print("Number of hits 2:", len(hits2))
for h in hits2[:5]:
    print(h)

db.close()
