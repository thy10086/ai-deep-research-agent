from fastapi import FastAPI

from app.api.routes.documents import router as documents_router


app = FastAPI(title="AI Deep Research Agent")

app.include_router(documents_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}