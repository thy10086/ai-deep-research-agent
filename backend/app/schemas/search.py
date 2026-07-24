from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=2,
        max_length=1000,
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
    )
    
    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError(
                "Query must contain at least two non-space characters."
            )

        return normalized

class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    token_count: int
    score: float
    metadata: dict[str, object]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]