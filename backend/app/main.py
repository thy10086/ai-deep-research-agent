from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.documents import router as documents_router
from app.api.routes.rag import router as rag_router
from app.api.routes.search import router as search_router
from app.core.config import settings
from app.api.routes.research import router as research_router
from app.services import health


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await health.close_dependencies()


app = FastAPI(
    title="AI Deep Research Agent",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(research_router, prefix="/api/v1")

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    try:
        await health.check_database()
        await health.check_redis()
    except (OSError, RedisError, SQLAlchemyError) as error:
        raise HTTPException(
            status_code=503,
            detail="A required service is unavailable.",
        ) from error

    return {"status": "ready"}
