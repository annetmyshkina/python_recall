from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class StructuredRequest:
    """Provider-neutral request for one validated JSON response."""

    scenario: str
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """Provider usage metadata used by later AI request logging."""

    input_tokens: int
    output_tokens: int
    total_duration_ns: int | None = None


@dataclass(frozen=True, slots=True)
class StructuredResult[ResultT: BaseModel]:
    """Validated provider result with transport metadata."""

    data: ResultT
    provider: str
    model: str
    usage: ProviderUsage


class AiProvider(Protocol):
    """Small provider boundary shared by all AI scenarios."""

    name: str
    model: str

    async def is_model_available(self) -> bool:
        """Return whether the configured model is installed."""

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        """Generate and validate one structured response."""
