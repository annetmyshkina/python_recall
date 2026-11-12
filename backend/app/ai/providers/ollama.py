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
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
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
        except ValidationError as error:
            raise AiProviderResponseError("Invalid structured AI response") from error

        try:
            data = response_model.model_validate_json(chat.message.content)
        except ValidationError as first_error:
            validation_errors = first_error.json(
                include_input=False,
                include_url=False,
            )[:4000]
            repair_instruction = (
                "ОБЯЗАТЕЛЬНО ИЗМЕНИ предыдущий JSON, не повторяй его. Он нарушил "
                "схему или правила проверки. Исправь все нарушения одновременно "
                "и верни полный JSON без дополнительного текста. Сохрани язык, "
                "заданный системной инструкцией. "
                f"{request.repair_prompt or ''} Ошибки проверки: "
                f"{validation_errors}"
            )
            repair_payload = {
                **payload,
                "messages": [
                    *messages,
                    {"role": "assistant", "content": chat.message.content},
                    {"role": "user", "content": repair_instruction},
                ],
            }
            repair_response = await self._request(
                "POST",
                "/api/chat",
                json=repair_payload,
            )
            try:
                repaired_chat = _OllamaChatResponse.model_validate_json(
                    repair_response.content
                )
                data = response_model.model_validate_json(repaired_chat.message.content)
            except ValidationError as error:
                raise AiProviderResponseError(
                    "Invalid structured AI response"
                ) from error
            usage = ProviderUsage(
                input_tokens=(chat.prompt_eval_count + repaired_chat.prompt_eval_count),
                output_tokens=chat.eval_count + repaired_chat.eval_count,
                total_duration_ns=_sum_optional_durations(
                    chat.total_duration,
                    repaired_chat.total_duration,
                ),
            )
            model = repaired_chat.model
        else:
            usage = ProviderUsage(
                input_tokens=chat.prompt_eval_count,
                output_tokens=chat.eval_count,
                total_duration_ns=chat.total_duration,
            )
            model = chat.model

        return StructuredResult(
            data=data,
            provider=self.name,
            model=model,
            usage=usage,
        )


def _sum_optional_durations(first: int | None, second: int | None) -> int | None:
    if first is None and second is None:
        return None
    return (first or 0) + (second or 0)
