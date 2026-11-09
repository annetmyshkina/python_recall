import httpx
import pytest
from fastapi import FastAPI

from backend.app.ai.manager import AiProviderState, AiProviderStatus
from backend.app.ai.providers.base import (
    StructuredModelT,
    StructuredRequest,
    StructuredResult,
)
from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.main import create_app


class StaticAiManager:
    def __init__(self, provider_status: AiProviderStatus) -> None:
        self.provider_status = provider_status

    async def get_status(self) -> AiProviderStatus:
        return self.provider_status

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        raise AssertionError("generation is not expected in diagnostic API tests")


def build_test_app(provider_status: AiProviderStatus) -> FastAPI:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
    )
    database = Database(settings.database_url)
    return create_app(settings, database, StaticAiManager(provider_status))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_status", "health_body"),
    [
        (
            AiProviderStatus("ollama", False, "disabled", "qwen3:4b"),
            {"status": "disabled", "provider": "ollama", "model": "qwen3:4b"},
        ),
        (
            AiProviderStatus("ollama", True, "ready", "qwen3:4b"),
            {"status": "ok", "provider": "ollama", "model": "qwen3:4b"},
        ),
    ],
)
async def test_ai_provider_and_health_success_states(
    provider_status: AiProviderStatus,
    health_body: dict[str, object],
) -> None:
    transport = httpx.ASGITransport(app=build_test_app(provider_status))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        providers = await client.get("/api/v1/ai/providers")
        health = await client.get("/api/v1/health/ai")

    assert providers.status_code == 200
    assert providers.json() == {
        "default_provider": "ollama",
        "items": [
            {
                "name": "ollama",
                "enabled": provider_status.enabled,
                "status": provider_status.status,
                "model": "qwen3:4b",
            }
        ],
    }
    assert health.status_code == 200
    assert health.json() == health_body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "error_code"),
    [
        ("unavailable", "ai_provider_unavailable"),
        ("model_missing", "ai_model_missing"),
    ],
)
async def test_ai_failure_is_diagnostic_and_does_not_break_core_health(
    state: AiProviderState,
    error_code: str,
) -> None:
    provider_status = AiProviderStatus("ollama", True, state, "qwen3:4b")
    transport = httpx.ASGITransport(app=build_test_app(provider_status))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        providers = await client.get("/api/v1/ai/providers")
        ai_health = await client.get("/api/v1/health/ai")
        core_health = await client.get("/api/v1/health")

    assert providers.status_code == 200
    assert providers.json()["items"][0]["status"] == state
    assert ai_health.status_code == 503
    assert ai_health.headers["content-type"] == "application/problem+json"
    assert ai_health.json()["code"] == error_code
    assert "private" not in ai_health.text
    assert core_health.status_code == 200
    assert core_health.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_generated_openapi_contains_ai_diagnostics() -> None:
    application = build_test_app(
        AiProviderStatus("ollama", False, "disabled", "qwen3:4b")
    )
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/openapi.json")

    document = response.json()
    assert (
        document["paths"]["/api/v1/ai/providers"]["get"]["operationId"]
        == "list_ai_providers"
    )
    assert (
        document["paths"]["/api/v1/health/ai"]["get"]["operationId"] == "get_ai_health"
    )
