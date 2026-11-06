from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Dependency-free Backend liveness response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str


class DatabaseHealthResponse(BaseModel):
    """Successful database readiness response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


class ProblemDetails(BaseModel):
    """RFC 9457-style stable error envelope fixed by the API contract."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    trace_id: str
    errors: list[dict[str, str]]
