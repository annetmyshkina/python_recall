from dataclasses import dataclass, field

from backend.app.core.schemas import ProblemField


@dataclass(slots=True)
class ApiError(Exception):
    """Expected application error safe to expose through the API."""

    status_code: int
    code: str
    title: str
    detail: str
    errors: list[ProblemField] = field(default_factory=list)


def resource_not_found(resource: str) -> ApiError:
    return ApiError(
        status_code=404,
        code="resource_not_found",
        title="Resource not found",
        detail=f"{resource} was not found.",
    )


def duplicate_resource(resource: str) -> ApiError:
    return ApiError(
        status_code=409,
        code="duplicate_resource",
        title="Duplicate resource",
        detail=f"{resource} with these unique fields already exists.",
    )


def deletion_restricted(detail: str) -> ApiError:
    return ApiError(
        status_code=409,
        code="deletion_restricted",
        title="Deletion is restricted",
        detail=detail,
    )


def database_unavailable() -> ApiError:
    return ApiError(
        status_code=503,
        code="database_unavailable",
        title="Database unavailable",
        detail="PostgreSQL is temporarily unavailable.",
    )


def card_archived() -> ApiError:
    return ApiError(
        status_code=409,
        code="card_archived",
        title="Card is archived",
        detail="Archived card cannot be used for learning operations.",
    )


def idempotency_conflict() -> ApiError:
    return ApiError(
        status_code=409,
        code="idempotency_conflict",
        title="Idempotency conflict",
        detail="Idempotency key was already used for a different request.",
    )


def review_conflict(detail: str) -> ApiError:
    return ApiError(
        status_code=409,
        code="review_conflict",
        title="Review conflict",
        detail=detail,
    )
