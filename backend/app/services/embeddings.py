from dataclasses import dataclass, field

import httpx

from app.core.config import settings


class EmbeddingServiceError(Exception):
    pass


class InvalidEmbeddingResponseError(EmbeddingServiceError):
    pass


@dataclass(frozen=True)
class OllamaEmbeddingService:
    base_url: str
    model: str
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

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                for start in range(0, len(texts), self.batch_size):
                    batch = texts[start : start + self.batch_size]
                    response = await client.post(
                        "/api/embed",
                        json={
                            "model": self.model,
                            "input": batch,
                        },
                    )
                    response.raise_for_status()

                    payload = response.json()
                    embeddings = payload.get("embeddings")

                    if (
                        not isinstance(embeddings, list)
                        or len(embeddings) != len(batch)
                    ):
                        raise InvalidEmbeddingResponseError(
                            "Embedding count does not match input count."
                        )

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


embedding_service = OllamaEmbeddingService(
    base_url=settings.embedding_base_url,
    model=settings.embedding_model,
)