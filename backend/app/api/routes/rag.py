from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.rag import Citation, RAGRequest, RAGResponse
from app.services.embeddings import EmbeddingServiceError
from app.services.llm import LLMServiceError
from app.services.rag import answer_question

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post(
    "/answer",
    response_model=RAGResponse,
)
async def generate_rag_answer(
    request: RAGRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RAGResponse:
    try:
        result = await answer_question(
            session=session,
            question=request.question,
            limit=request.limit,
        )
    except EmbeddingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The embedding service is unavailable.",
        ) from error
    except LLMServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language model service is unavailable.",
        ) from error

    return RAGResponse(
        question=request.question,
        answer=result.answer,
        citations=[
            Citation(
                index=index,
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                filename=source.filename,
                content=source.content,
                score=source.score,
            )
            for index, source in enumerate(
                result.sources,
                start=1,
            )
        ],
    )