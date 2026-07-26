from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=2000,
    )

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError(
                "Question must contain at least two non-space characters."
            )

        return normalized


class ResearchEvidence(BaseModel):
    index: int
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    score: float


class ResearchResponse(BaseModel):
    question: str
    subquestions: list[str]
    report: str
    evidence: list[ResearchEvidence]