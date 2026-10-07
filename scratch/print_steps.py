import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

log_path = r"C:\Users\Subham Patnaik\.gemini\antigravity-ide\brain\82ae6040-2558-4ca4-8d8d-0132b1d761bc\.system_generated\logs\transcript.jsonl"
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        if d.get("step_index") in [410, 562, 694, 807]:
            print(f"=== STEP {d.get('step_index')} ===")
            print(d.get("content"))
