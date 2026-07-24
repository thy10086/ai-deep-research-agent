from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RAGRequest(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=2000,
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
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


class Citation(BaseModel):
    index: int
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    score: float


class RAGResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]