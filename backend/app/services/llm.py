from dataclasses import dataclass, field
import json

import httpx

from app.core.config import settings


class LLMServiceError(Exception):
    pass


class InvalidLLMResponseError(LLMServiceError):
    pass


@dataclass(frozen=True)
class OpenAICompatibleLLMService:
    base_url: str
    model: str
    api_key: str = ""
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
        json_mode: bool = False,
    ) -> str:
        request_payload: dict[str, object] = {
            "model": self.model,
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
            "temperature": 0.2,
        }
        if json_mode:
            request_payload["response_format"] = {
                "type": "json_object",
            }

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    json=request_payload,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPError as error:
            raise LLMServiceError(
                "Failed to call the language model service."
            ) from error

        payload = response.json()
        choices = payload.get("choices")

        if not isinstance(choices, list) or not choices:
            raise InvalidLLMResponseError(
                "Language model response has no choices."
            )

        choice = choices[0]
        if not isinstance(choice, dict):
            raise InvalidLLMResponseError(
                "Language model response has an invalid choice."
            )

        message = choice.get("message")

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

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, object]:
        content = await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise InvalidLLMResponseError(
                "Language model returned invalid JSON."
            ) from error

        if not isinstance(payload, dict):
            raise InvalidLLMResponseError(
                "Language model JSON response must be an object."
            )

        return payload


llm_service = OpenAICompatibleLLMService(
    base_url=settings.llm_base_url,
    model=settings.llm_model,
    api_key=settings.llm_api_key,
)
