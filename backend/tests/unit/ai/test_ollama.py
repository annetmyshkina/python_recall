import json

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from backend.app.ai.providers.base import StructuredRequest
from backend.app.ai.providers.errors import (
    AiProviderResponseError,
    AiProviderTimeoutError,
    AiProviderUnavailableError,
)
from backend.app.ai.providers.ollama import OllamaProvider
from backend.app.core.config import Settings


class ExampleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: str
    confidence: float


def build_provider(
    handler: httpx.MockTransport,
    **settings_overrides: object,
) -> OllamaProvider:
    settings = Settings(
        _env_file=None,
        ollama_model="qwen3:4b",
        **settings_overrides,
    )
    return OllamaProvider(settings, transport=handler)


@pytest.mark.asyncio
async def test_model_readiness_matches_name_or_model_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "other:latest", "model": "qwen3:4b"}]},
        )

    provider = build_provider(httpx.MockTransport(handler))

    assert await provider.is_model_available() is True


@pytest.mark.asyncio
async def test_model_readiness_reports_missing_model() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"models": [{"name": "llama3.2:3b"}]})
    )

    assert await build_provider(transport).is_model_available() is False


@pytest.mark.asyncio
async def test_structured_generation_sends_schema_and_validates_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3:4b"
        assert payload["stream"] is False
        assert payload["think"] is False
        assert payload["format"] == ExampleResult.model_json_schema()
        assert payload["options"] == {"temperature": 0.0, "num_predict": 1024}
        assert payload["messages"] == [
            {"role": "system", "content": "Return JSON."},
            {"role": "user", "content": "Evaluate this."},
        ]
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"verdict": "correct", "confidence": 0.9}),
                },
                "prompt_eval_count": 20,
                "eval_count": 8,
                "total_duration": 123,
            },
        )

    provider = build_provider(httpx.MockTransport(handler))
    result = await provider.generate_structured(
        StructuredRequest(
            scenario="test",
            system_prompt="Return JSON.",
            user_prompt="Evaluate this.",
        ),
        ExampleResult,
    )

    assert result.data == ExampleResult(verdict="correct", confidence=0.9)
    assert result.provider == "ollama"
    assert result.model == "qwen3:4b"
    assert result.usage.input_tokens == 20
    assert result.usage.output_tokens == 8
    assert result.usage.total_duration_ns == 123


@pytest.mark.asyncio
async def test_provider_maps_timeout_without_leaking_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private transport detail", request=request)

    provider = build_provider(httpx.MockTransport(handler))

    with pytest.raises(AiProviderTimeoutError, match="timed out") as captured:
        await provider.is_model_available()

    assert "private transport detail" not in str(captured.value)


@pytest.mark.asyncio
async def test_provider_maps_http_error() -> None:
    provider = build_provider(
        httpx.MockTransport(
            lambda _: httpx.Response(500, json={"error": "private provider detail"})
        )
    )

    with pytest.raises(AiProviderUnavailableError, match="HTTP error") as captured:
        await provider.is_model_available()

    assert "private provider detail" not in str(captured.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"unexpected": []}),
    ],
)
async def test_provider_rejects_invalid_model_list(response: httpx.Response) -> None:
    provider = build_provider(httpx.MockTransport(lambda _: response))

    with pytest.raises(AiProviderResponseError, match="Invalid model list"):
        await provider.is_model_available()


@pytest.mark.asyncio
async def test_provider_rejects_invalid_structured_content() -> None:
    provider = build_provider(
        httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "model": "qwen3:4b",
                    "message": {"role": "assistant", "content": "{}"},
                },
            )
        )
    )

    with pytest.raises(AiProviderResponseError, match="structured"):
        await provider.generate_structured(
            StructuredRequest("test", "system", "user"),
            ExampleResult,
        )


@pytest.mark.asyncio
async def test_provider_rejects_oversized_response() -> None:
    provider = build_provider(
        httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 1025)),
        ai_max_response_bytes=1024,
    )

    with pytest.raises(AiProviderResponseError, match="too large"):
        await provider.is_model_available()
