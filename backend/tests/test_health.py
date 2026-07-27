import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def available() -> None:
        return None

    monkeypatch.setattr(
        "app.services.health.check_database",
        available,
    )
    monkeypatch.setattr(
        "app.services.health.check_redis",
        available,
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_check_reports_dependency_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable() -> None:
        raise RedisConnectionError("unavailable")

    monkeypatch.setattr(
        "app.services.health.check_database",
        unavailable,
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "A required service is unavailable."
    }
