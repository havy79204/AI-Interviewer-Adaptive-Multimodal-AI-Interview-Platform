"""Interview assessment and review schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SkillAssessment(BaseModel):
    """Assessment of one skill during an interview."""

    skill_name: str
    score: float = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = []
    category: Optional[str] = None


class AnswerEvaluation(BaseModel):
    """Evaluation of a candidate answer."""

    answer: str
    score: float = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    skills_detected: dict[str, float] = {}
    strengths: list[str] = []
    weaknesses: list[str] = []
    feedback: Optional[str] = None
    evidence: list[str] = []


class SkillScore(BaseModel):
    """Final score for one skill."""

    skill: str
    score: float = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    evidence: int = 0


class CandidateReport(BaseModel):
    """Final interview report."""

    candidate_id: UUID
    interview_id: UUID
    position: str
    overall_score: float = Field(ge=0, le=100)
    technical_score: float = Field(ge=0, le=10)
    communication_score: float = Field(ge=0, le=10)
    problem_solving_score: float = Field(ge=0, le=10)
    skills: list[SkillScore] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendation: str
    confidence: float = Field(ge=0, le=1)
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)
