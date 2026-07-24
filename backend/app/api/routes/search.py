from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.search import semantic_search
from app.services.embeddings import EmbeddingServiceError

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "",
    response_model=SearchResponse,
)
async def search_documents(
    request: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SearchResponse:
    try:
        hits = await semantic_search(
            session=session,
            query=request.query,
            limit=request.limit,
        )
    except EmbeddingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The embedding service is unavailable.",
        ) from error

    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                filename=hit.filename,
                content=hit.content,
                token_count=hit.token_count,
                score=hit.score,
                metadata=hit.metadata,
            )
            for hit in hits
        ],
    )