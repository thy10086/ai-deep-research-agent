from dataclasses import dataclass, field

import httpx

from app.core.config import settings


class EmbeddingServiceError(Exception):
    pass


class InvalidEmbeddingResponseError(EmbeddingServiceError):
    pass


@dataclass(frozen=True)
class OpenAICompatibleEmbeddingService:
    base_url: str
    model: str
    api_key: str = ""
    expected_dimension: int = 1024
    batch_size: int = 32
    timeout_seconds: float = 120.0
    
    transport: httpx.AsyncBaseTransport | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                for start in range(0, len(texts), self.batch_size):
                    batch = texts[start : start + self.batch_size]
                    response = await client.post(
                        "/embeddings",
                        json={
                            "model": self.model,
                            "input": batch,
                            "encoding_format": "float",
                        },
                        headers=headers,
                    )
                    response.raise_for_status()

                    payload = response.json()
                    data = payload.get("data")

                    if (
                        not isinstance(data, list)
                        or len(data) != len(batch)
                    ):
                        raise InvalidEmbeddingResponseError(
                            "Embedding count does not match input count."
                        )

                    embeddings = []
                    for item in data:
                        if not isinstance(item, dict):
                            raise InvalidEmbeddingResponseError(
                                "Embedding response item is invalid."
                            )
                        embeddings.append(item.get("embedding"))

                    all_embeddings.extend(
                        self._validate_embeddings(embeddings)
                    )
        except httpx.HTTPError as error:
            raise EmbeddingServiceError(
                "Failed to call the embedding service."
            ) from error

        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    def _validate_embeddings(
        self,
        embeddings: list[object],
    ) -> list[list[float]]:
        validated: list[list[float]] = []

        for embedding in embeddings:
            if not isinstance(embedding, list):
                raise InvalidEmbeddingResponseError(
                    "Embedding must be a list."
                )

            if len(embedding) != self.expected_dimension:
                raise InvalidEmbeddingResponseError(
                    "Unexpected embedding dimension."
                )

            if not all(
                isinstance(value, int | float)
                for value in embedding
            ):
                raise InvalidEmbeddingResponseError(
                    "Embedding contains non-numeric values."
                )

            validated.append(
                [float(value) for value in embedding]
            )

        return validated


embedding_service = OpenAICompatibleEmbeddingService(
    base_url=settings.embedding_base_url,
    model=settings.embedding_model,
    api_key=settings.embedding_api_key or settings.llm_api_key,
)
