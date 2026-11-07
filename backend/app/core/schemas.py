from pydantic import BaseModel, ConfigDict, Field


class ApiSchema(BaseModel):
    """Strict API schema with ORM attribute support."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Pagination(ApiSchema):
    """Shared page metadata."""

    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class Page[ItemT](ApiSchema):
    """Generic paginated response envelope."""

    items: list[ItemT]
    pagination: Pagination


class ProblemField(ApiSchema):
    """One validation issue in a Problem Details response."""

    field: str
    code: str
    message: str


class ProblemDetails(ApiSchema):
    """Stable error envelope used by every API endpoint."""

    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    instance: str
    code: str
    trace_id: str
    errors: list[ProblemField]
