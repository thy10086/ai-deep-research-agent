import pytest
from pydantic import ValidationError

from app.schemas.search import SearchRequest
from fastapi.testclient import TestClient

from app.main import app
from app.services.embeddings import EmbeddingServiceError

def test_search_request_normalizes_query() -> None:
    request = SearchRequest(
        query="  semantic retrieval  ",
    )

    assert request.query == "semantic retrieval"
    assert request.limit == 5


@pytest.mark.parametrize(
    "query",
    [
        "  ",
        " a ",
    ],
)
def test_search_request_rejects_short_query(query: str) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query=query)


@pytest.mark.parametrize(
    "limit",
    [
        0,
        21,
    ],
)
def test_search_request_rejects_invalid_limit(limit: int) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            query="semantic retrieval",
            limit=limit,
        )

def test_search_returns_503_when_embedding_service_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable_search(*args: object, **kwargs: object) -> list:
        raise EmbeddingServiceError

    monkeypatch.setattr(
        "app.api.routes.search.semantic_search",
        unavailable_search,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/search",
        json={
            "query": "semantic retrieval",
            "limit": 5,
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The embedding service is unavailable."
    }