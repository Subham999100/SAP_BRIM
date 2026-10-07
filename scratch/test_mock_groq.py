from groq import Groq

class FakeChoice:
    message = type("Msg", (), {"content": "First Second Third"})()
class FakeResponse:
    choices = [FakeChoice()]

Groq.chat = type("Chat", (), {"completions": type("Comp", (), {"create": lambda *a, **k: FakeResponse()})()})()

from backend.app.services.llm_service import llm_service
evidence = [{"chunk_id": "c1", "document_name": "SAP CC.pdf", "chunk_text": "Chunk Word Four", "rerank_score": 0.9}]
tokens = list(llm_service.stream_answer("query", evidence))
joined = "".join(tokens).strip()
print("stream_answer tokens:", tokens)
print("stream_answer joined:", joined)
assert joined == "First Second Third"
print("SUCCESS!")
