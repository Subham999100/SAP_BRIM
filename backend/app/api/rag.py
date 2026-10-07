from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from backend.app.services.rag_service import rag_service
from backend.app.models.user import User
from backend.app.models.chat import Chat
from backend.app.security.auth import get_current_user


router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query", response_model=RAGQueryResponse)
def query_rag(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify that the chat belongs to the logged-in user if specified
    if request.chat_id:
        chat = db.query(Chat).filter(
            Chat.id == request.chat_id,
            Chat.user_id == current_user.id
        ).first()

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )

    # 2. Run authoritative unified RAG pipeline
    try:
        result = rag_service.process_query(
            db=db,
            query=request.query,
            chat_id=request.chat_id,
            user_id=current_user.id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the SAP query: {str(e)}"
        )

    # 3. Return response conforming strictly to RAGQueryResponse schema
    return RAGQueryResponse(
        answer=result["answer"],
        source_type=result["source_type"],
        grounding_score=result["grounding_score"],
        citations=result["citations"],
        web_sources=result["web_sources"],
        chat_id=result.get("chat_id"),
        message_id=result.get("message_id")
    )