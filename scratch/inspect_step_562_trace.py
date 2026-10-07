import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

log_path = r"C:\Users\Subham Patnaik\.gemini\antigravity-ide\brain\82ae6040-2558-4ca4-8d8d-0132b1d761bc\.system_generated\logs\transcript.jsonl"
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        if 562 <= d.get("step_index", 0) <= 693 and d.get("type") == "PLANNER_RESPONSE":
            content = d.get("content", "")
            if "EVALUAT" in content.upper() or "4/10" in content or "TRACE" in content.upper() or "GENERATED ANSWER" in content.upper():
                print(f"=== STEP {d.get('step_index')} ===")
                print(content[:1500])
                print("\n" + "="*40 + "\n")
