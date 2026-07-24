from dataclasses import dataclass, field

import httpx

from app.core.config import settings


class LLMServiceError(Exception):
    pass


class InvalidLLMResponseError(LLMServiceError):
    pass


@dataclass(frozen=True)
class OllamaLLMService:
    base_url: str
    model: str
    timeout_seconds: float = 180.0

    transport: httpx.AsyncBaseTransport | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    "/api/chat",
                    json={
                        "model": self.model,
                        "stream": False,
                        "think": False,
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        "options": {
                            "temperature": 0.2,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as error:
            raise LLMServiceError(
                "Failed to call the language model service."
            ) from error

        payload = response.json()
        message = payload.get("message")

        if not isinstance(message, dict):
            raise InvalidLLMResponseError(
                "Language model response has no message."
            )

        content = message.get("content")

        if not isinstance(content, str) or not content.strip():
            raise InvalidLLMResponseError(
                "Language model returned empty content."
            )

        return content.strip()


llm_service = OllamaLLMService(
    base_url=settings.llm_base_url,
    model=settings.llm_model,
)