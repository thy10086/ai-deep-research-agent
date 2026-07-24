from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.api.routes.search import router as search_router

app = FastAPI(title="AI Deep Research Agent")

app.include_router(documents_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}