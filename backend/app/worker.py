from typing import Any

from arq.connections import RedisSettings

from app.core.config import settings
from app.db.session import async_session_factory
from app.services.research_agent import run_deep_research


async def run_research_job(
    context: dict[str, Any],
    question: str,
) -> dict[str, Any]:
    async with async_session_factory() as session:
        result = await run_deep_research(
            session=session,
            question=question,
        )

    return {
        "question": result.question,
        "subquestions": result.subquestions,
        "report": result.report,
        "evidence": [
            {
                "index": index,
                "chunk_id": str(hit.chunk_id),
                "document_id": str(hit.document_id),
                "filename": hit.filename,
                "content": hit.content,
                "score": hit.score,
            }
            for index, hit in enumerate(result.evidence, start=1)
        ],
    }


class WorkerSettings:
    functions = [run_research_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 900
    keep_result = 3600