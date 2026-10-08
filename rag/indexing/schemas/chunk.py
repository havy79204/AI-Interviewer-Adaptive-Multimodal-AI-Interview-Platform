"""Conversation, question, and media chunk schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """Single question-and-answer turn."""

    role: str
    content: str
    timestamp: datetime
    duration: Optional[int] = None


class QuestionResponse(BaseModel):
    """Question presented to a candidate."""

    question: str
    question_id: UUID
    category: str
    difficulty: str
    follow_up: bool = False
    context: Optional[str] = None


class AudioChunk(BaseModel):
    """Audio data chunk."""

    data: bytes
    sample_rate: int = 16000
    duration: float


class Transcript(BaseModel):
    """Speech-to-text result."""

    text: str
    confidence: float = Field(ge=0, le=1)
    language: str = "en"
    duration: float
