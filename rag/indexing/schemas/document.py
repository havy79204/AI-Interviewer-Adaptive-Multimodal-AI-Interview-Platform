"""Document schemas used by retrieval and indexing."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class Document(BaseModel):
    """RAG document."""

    id: UUID
    content: str
    metadata: dict[str, Any]
    embedding: Optional[list[float]] = None
    source: str = "unknown"


class RetrievalResult(BaseModel):
    """Documents returned for a retrieval query."""

    documents: list[Document]
    scores: list[float]
    query: str
