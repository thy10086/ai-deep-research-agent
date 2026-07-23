from fastapi import FastAPI

app = FastAPI(title="AI Deep Research Agent")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}