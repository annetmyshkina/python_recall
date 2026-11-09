from typing import Any

import pytest
from pydantic import BaseModel

from backend.app.ai.manager import AiProviderManager
from backend.app.ai.providers.base import StructuredRequest
from backend.app.ai.providers.errors import (
    AiDisabledError,
    AiModelMissingError,
    AiProviderUnavailableError,
)
from backend.app.core.config import Settings


class StubProvider:
    name = "ollama"
    model = "qwen3:4b"

    def __init__(self, availability: bool | Exception) -> None:
        self.availability = availability
        self.readiness_calls = 0

    async def is_model_available(self) -> bool:
        self.readiness_calls += 1
        if isinstance(self.availability, Exception):
            raise self.availability
        return self.availability

    async def generate_structured(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("generation is not expected in these tests")


@pytest.mark.asyncio
async def test_disabled_manager_does_not_contact_provider() -> None:
    provider = StubProvider(True)
    manager = AiProviderManager(Settings(_env_file=None), provider)

    result = await manager.get_status()

    assert result.status == "disabled"
    assert result.enabled is False
    assert provider.readiness_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("availability", "expected"),
    [
        (True, "ready"),
        (False, "model_missing"),
        (AiProviderUnavailableError("private detail"), "unavailable"),
    ],
)
async def test_enabled_manager_maps_readiness_state(
    availability: bool | Exception,
    expected: str,
) -> None:
    manager = AiProviderManager(
        Settings(_env_file=None, ai_enabled=True),
        StubProvider(availability),
    )

    result = await manager.get_status()

    assert result.status == expected
    assert result.enabled is True


@pytest.mark.asyncio
async def test_disabled_manager_rejects_generation_without_provider_call() -> None:
    provider = StubProvider(True)
    manager = AiProviderManager(Settings(_env_file=None), provider)

    with pytest.raises(AiDisabledError):
        await manager.generate_structured(
            StructuredRequest("test", "system", "user"),
            BaseModel,
        )

    assert provider.readiness_calls == 0


@pytest.mark.asyncio
async def test_manager_rejects_generation_when_model_is_missing() -> None:
    manager = AiProviderManager(
        Settings(_env_file=None, ai_enabled=True),
        StubProvider(False),
    )

    with pytest.raises(AiModelMissingError):
        await manager.generate_structured(
            StructuredRequest("test", "system", "user"),
            BaseModel,
        )
