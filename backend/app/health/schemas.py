from typing import Literal

from backend.app.core.schemas import ApiSchema


class HealthResponse(ApiSchema):
    """Dependency-free Backend liveness response."""

    status: Literal["ok"]
    service: str
    version: str


class DatabaseHealthResponse(ApiSchema):
    """Successful database readiness response."""

    status: Literal["ok"]
