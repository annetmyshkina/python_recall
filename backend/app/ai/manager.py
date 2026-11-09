from dataclasses import dataclass
from typing import Literal, Protocol

from backend.app.ai.providers.base import (
    AiProvider,
    StructuredModelT,
    StructuredRequest,
    StructuredResult,
)
from backend.app.ai.providers.errors import (
    AiDisabledError,
    AiModelMissingError,
    AiProviderError,
)
from backend.app.ai.providers.ollama import OllamaProvider
from backend.app.core.config import Settings

AiProviderName = Literal["ollama"]
AiProviderState = Literal["disabled", "ready", "unavailable", "model_missing"]


@dataclass(frozen=True, slots=True)
class AiProviderStatus:
    name: AiProviderName
    enabled: bool
    status: AiProviderState
    model: str


class AiManager(Protocol):
    """Application-facing AI boundary suitable for test doubles."""

    async def get_status(self) -> AiProviderStatus:
        """Return the current optional provider state."""

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        """Generate only when AI is enabled and its model is available."""


class AiProviderManager:
    """Own optional-AI policy independently from individual scenarios."""

    def __init__(
        self,
        settings: Settings,
        provider: AiProvider | None = None,
    ) -> None:
        self._enabled = settings.ai_enabled
        self._provider = provider or OllamaProvider(settings)

    async def get_status(self) -> AiProviderStatus:
        if not self._enabled:
            state: AiProviderState = "disabled"
        else:
            try:
                model_available = await self._provider.is_model_available()
            except AiProviderError:
                state = "unavailable"
            else:
                state = "ready" if model_available else "model_missing"

        return AiProviderStatus(
            name="ollama",
            enabled=self._enabled,
            status=state,
            model=self._provider.model,
        )

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        if not self._enabled:
            raise AiDisabledError("AI is disabled")
        model_available = await self._provider.is_model_available()
        if not model_available:
            raise AiModelMissingError("Configured AI model is not installed")
        return await self._provider.generate_structured(request, response_model)
