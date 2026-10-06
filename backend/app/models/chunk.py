import uuid
import json
from typing import List
from sqlalchemy import Column, String, Integer, Text, ForeignKey, TypeDecorator
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from backend.app.database import Base
from backend.app.config import settings

class EmbeddingVector(TypeDecorator):
    """Platform-independent vector type that uses pgvector on Postgres and JSON on SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(settings.EMBEDDING_DIM))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, (list, tuple)):
            return json.dumps(list(value))
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            if hasattr(value, "tolist"):
                return value.tolist()
            return list(value)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return []
        return value

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    document_name = Column(String(255), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    section = Column(String(255), nullable=True)
    chunk_text = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    embedding = Column(EmbeddingVector, nullable=False)

    document = relationship("Document", back_populates="chunks")
