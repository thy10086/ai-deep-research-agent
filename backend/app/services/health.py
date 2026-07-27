from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


redis_client: Redis = redis_from_url(
    settings.redis_url,
    decode_responses=True,
)


async def check_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def check_redis() -> None:
    await redis_client.ping()


async def close_dependencies() -> None:
    await redis_client.aclose()
    await engine.dispose()
