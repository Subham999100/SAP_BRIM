from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.chat import Chat
from backend.app.models.message import Message
from backend.app.schemas.message import MessageCreate, MessageResponse
from backend.app.security.auth import get_current_user
from backend.app.services.rag_service import rag_service

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["Messages"])


def verify_chat_ownership(chat_id: str, user_id: str, db: Session) -> Chat:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


@router.get("", response_model=List[MessageResponse])
def get_messages(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_chat_ownership(chat_id, current_user.id, db)
    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    result = []
    for msg in messages:
        c_list = [
            {
                "id": c.id,
                "document": c.document_name,
                "page": c.page_number,
                "section": c.section,
                "score": c.similarity_score,
                "snippet": c.citation_text
            }
            for c in msg.citations
        ]
        w_list = [
            {
                "id": w.id,
                "title": w.title,
                "url": w.url,
                "domain": w.domain,
                "snippet": w.snippet
            }
            for w in msg.web_sources
        ]
        result.append(
            MessageResponse(
                id=msg.id,
                chat_id=msg.chat_id,
                role=msg.role,
                content=msg.content,
                source_type=msg.source_type,
                grounding_score=msg.grounding_score,
                created_at=msg.created_at,
                citations=c_list,
                web_sources=w_list
            )
        )
    return result


@router.post("")
def send_message(
    chat_id: str,
    msg_in: MessageCreate,
    stream: bool = Query(False, description="Enable Server-Sent Events (SSE) streaming"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_chat_ownership(chat_id, current_user.id, db)

    # 1. Genuine SSE Streaming Flow
    if stream:
        return StreamingResponse(
            rag_service.stream_query(
                db=db,
                query=msg_in.content.strip(),
                chat_id=chat_id,
                user_id=current_user.id
            ),
            media_type="text/event-stream"
        )

    # 2. Synchronous Unified RAG Flow
    rag_result = rag_service.process_query(
        db=db,
        query=msg_in.content.strip(),
        chat_id=chat_id,
        user_id=current_user.id
    )

    # 3. Retrieve persisted assistant message to return complete schema
    assistant_msg = None
    if rag_result.get("message_id"):
        assistant_msg = db.query(Message).filter(Message.id == rag_result["message_id"]).first()

    if assistant_msg:
        return MessageResponse(
            id=assistant_msg.id,
            chat_id=assistant_msg.chat_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            source_type=assistant_msg.source_type,
            grounding_score=assistant_msg.grounding_score,
            created_at=assistant_msg.created_at,
            citations=[
                {
                    "id": c.id,
                    "document": c.document_name,
                    "page": c.page_number,
                    "section": c.section,
                    "score": c.similarity_score,
                    "snippet": c.citation_text
                }
                for c in assistant_msg.citations
            ],
            web_sources=[
                {
                    "id": w.id,
                    "title": w.title,
                    "url": w.url,
                    "domain": w.domain,
                    "snippet": w.snippet
                }
                for w in assistant_msg.web_sources
            ]
        )

    return MessageResponse(
        id="msg-fallback",
        chat_id=chat_id,
        role="assistant",
        content=rag_result["answer"],
        source_type=rag_result["source_type"],
        grounding_score=rag_result["grounding_score"],
        created_at=datetime.now(timezone.utc),
        citations=rag_result.get("citations", []),
        web_sources=rag_result.get("web_sources", [])
    )
