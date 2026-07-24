from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.services.embeddings import embedding_service


@dataclass(frozen=True)
class SearchHit:
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    token_count: int
    score: float
    metadata: dict[str, object]


async def semantic_search(
    session: AsyncSession,
    query: str,
    limit: int,
) -> list[SearchHit]:
    query_embedding = await embedding_service.embed_query(query)

    cosine_distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )
    similarity_score = (1 - cosine_distance).label("score")

    statement = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id,
            Document.filename,
            DocumentChunk.content,
            DocumentChunk.token_count,
            DocumentChunk.attributes,
            similarity_score,
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            Document.status == "ready",
            DocumentChunk.embedding.is_not(None),
        )
        .order_by(cosine_distance)
        .limit(limit)
    )

    rows = (await session.execute(statement)).all()

    return [
        SearchHit(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            filename=row.filename,
            content=row.content,
            token_count=row.token_count,
            score=float(row.score),
            metadata=row.attributes,
        )
        for row in rows
    ]