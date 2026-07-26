from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.research import (
    ResearchEvidence,
    ResearchRequest,
    ResearchResponse,
)
from app.services.embeddings import EmbeddingServiceError
from app.services.llm import LLMServiceError
from app.services.research_agent import run_deep_research

router = APIRouter(prefix="/research", tags=["research"])


@router.post(
    "",
    response_model=ResearchResponse,
)
async def create_research_report(
    request: ResearchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchResponse:
    try:
        result = await run_deep_research(
            session=session,
            question=request.question,
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

    return ResearchResponse(
        question=result.question,
        subquestions=result.subquestions,
        report=result.report,
        evidence=[
            ResearchEvidence(
                index=index,
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                filename=hit.filename,
                content=hit.content,
                score=hit.score,
            )
            for index, hit in enumerate(
                result.evidence,
                start=1,
            )
        ],
    )