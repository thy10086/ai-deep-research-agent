import json

import httpx
import pytest

from app.services.embeddings import (
    EmbeddingServiceError,
    InvalidEmbeddingResponseError,
    OpenAICompatibleEmbeddingService,
)


@pytest.mark.asyncio
async def test_embed_texts_batches_requests() -> None:
    received_batches: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        received_batches.append(payload["input"])

        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [float(index), 0.5, 1.0]}
                    for index, _ in enumerate(payload["input"])
                ]
            },
        )

    service = OpenAICompatibleEmbeddingService(
        base_url="http://embedding.test",
        model="test-model",
        expected_dimension=3,
        batch_size=2,
        transport=httpx.MockTransport(handler),
    )

    embeddings = await service.embed_texts(
        ["first", "second", "third"]
    )

    assert received_batches == [
        ["first", "second"],
        ["third"],
    ]
    assert len(embeddings) == 3
    assert all(len(embedding) == 3 for embedding in embeddings)


@pytest.mark.asyncio
async def test_embed_query_returns_single_vector() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
        )

    service = OpenAICompatibleEmbeddingService(
        base_url="http://embedding.test",
        model="test-model",
        expected_dimension=3,
        transport=httpx.MockTransport(handler),
    )

    assert await service.embed_query("query") == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embed_texts_rejects_wrong_dimension() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2]}]},
        )

    service = OpenAICompatibleEmbeddingService(
        base_url="http://embedding.test",
        model="test-model",
        expected_dimension=3,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(InvalidEmbeddingResponseError):
        await service.embed_texts(["document"])


@pytest.mark.asyncio
async def test_embed_texts_converts_http_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    service = OpenAICompatibleEmbeddingService(
        base_url="http://embedding.test",
        model="test-model",
        expected_dimension=3,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmbeddingServiceError):
        await service.embed_texts(["document"])
