from typing import Literal

from pydantic import Field

from backend.app.core.schemas import ApiSchema

AiProviderName = Literal["ollama"]
AiProviderState = Literal["disabled", "ready", "unavailable", "model_missing"]


class AiProviderResponse(ApiSchema):
    """Diagnostic state of one configured provider."""

    name: AiProviderName
    enabled: bool
    status: AiProviderState
    model: str = Field(min_length=1, max_length=200)


class AiProvidersResponse(ApiSchema):
    """Provider inventory; Release 3 supports one local provider."""

    default_provider: AiProviderName
    items: list[AiProviderResponse] = Field(min_length=1, max_length=1)
