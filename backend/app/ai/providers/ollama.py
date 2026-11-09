from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.ai.providers.base import (
    ProviderUsage,
    StructuredModelT,
    StructuredRequest,
    StructuredResult,
)
from backend.app.ai.providers.errors import (
    AiProviderResponseError,
    AiProviderTimeoutError,
    AiProviderUnavailableError,
)
from backend.app.core.config import Settings


class _OllamaModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    model: str | None = None


class _OllamaTagsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    models: list[_OllamaModel]


class _OllamaMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    content: str


class _OllamaChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str
    message: _OllamaMessage
    prompt_eval_count: int = Field(default=0, ge=0)
    eval_count: int = Field(default=0, ge=0)
    total_duration: int | None = Field(default=None, ge=0)


class OllamaProvider:
    """Direct asynchronous adapter for Ollama's local HTTP API."""

    name = "ollama"

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = settings.ollama_model
        self._base_url = settings.ollama_base_url
        self._timeout = settings.ai_timeout_seconds
        self._keep_alive = settings.ai_keep_alive
        self._max_output_tokens = settings.ai_max_output_tokens
        self._max_response_bytes = settings.ai_max_response_bytes
        self._temperature = settings.ai_temperature
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
            transport=self._transport,
            trust_env=False,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            async with self._client() as client:
                response = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise AiProviderTimeoutError("AI provider request timed out") from error
        except httpx.RequestError as error:
            raise AiProviderUnavailableError("AI provider is unavailable") from error

        if len(response.content) > self._max_response_bytes:
            raise AiProviderResponseError("AI provider response is too large")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise AiProviderUnavailableError(
                "AI provider returned an HTTP error"
            ) from error
        return response

    async def is_model_available(self) -> bool:
        response = await self._request("GET", "/api/tags")
        try:
            tags = _OllamaTagsResponse.model_validate_json(response.content)
        except ValidationError as error:
            raise AiProviderResponseError("Invalid model list response") from error

        installed_names = {
            candidate
            for item in tags.models
            for candidate in (item.name, item.model)
            if candidate is not None
        }
        return self.model in installed_names

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "think": False,
            "format": response_model.model_json_schema(),
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_output_tokens,
            },
        }
        response = await self._request("POST", "/api/chat", json=payload)
        try:
            chat = _OllamaChatResponse.model_validate_json(response.content)
            data = response_model.model_validate_json(chat.message.content)
        except ValidationError as error:
            raise AiProviderResponseError("Invalid structured AI response") from error

        return StructuredResult(
            data=data,
            provider=self.name,
            model=chat.model,
            usage=ProviderUsage(
                input_tokens=chat.prompt_eval_count,
                output_tokens=chat.eval_count,
                total_duration_ns=chat.total_duration,
            ),
        )
