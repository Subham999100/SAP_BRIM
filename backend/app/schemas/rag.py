from typing import List, Optional
from pydantic import BaseModel
from backend.app.schemas.citation import CitationResponse, WebSourceResponse

class RAGQueryRequest(BaseModel):
    chat_id: Optional[str] = None
    query: str

class RAGQueryResponse(BaseModel):
    answer: str
    source_type: str  # 'knowledge_base', 'web', 'refusal', 'error'
    grounding_score: float
    citations: List[CitationResponse] = []
    web_sources: List[WebSourceResponse] = []
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
