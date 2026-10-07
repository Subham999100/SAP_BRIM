import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"c:\Users\Subham Patnaik\OneDrive\Desktop\agent\SAP_Project")

from backend.app.database import SessionLocal
from backend.app.services.rag_service import rag_service

questions = [
    "What is a Price Plan in SAP Convergent Charging, and what role does it play in determining the price of a chargeable service?",
    "What is the difference between a Price Plan and a Price Table in SAP Convergent Charging?",
    "Design a telecom pricing scenario using SAP Convergent Charging."
]

db = SessionLocal()
try:
    for idx, q in enumerate(questions, start=1):
        print(f"\n{'='*80}")
        print(f"QUESTION {idx}:")
        print(q)
        print('='*80)
        
        result = rag_service.process_query(db, q)
        answer = result.get("answer", "")
        grounding_score = result.get("grounding_score", 0.0)
        citations = result.get("citations", [])
        
        print(f"\n[Grounding Score: {grounding_score}] [Citations: {len(citations)}]")
        print("\nGENERATED ANSWER:\n")
        print(answer)
        print("\n" + "-"*80)
        
        ans_lower = answer.lower()
        if "pricing specialist" in ans_lower[:200]:
            print(f"WARNING: Answer begins with Pricing Specialist duties!")
        else:
            print(f"VERIFIED: Answer directly addresses the target concept without opening with Pricing Specialist role.")

finally:
    db.close()
