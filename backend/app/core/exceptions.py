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


def ai_provider_unavailable() -> ApiError:
    return ApiError(
        status_code=503,
        code="ai_provider_unavailable",
        title="ИИ-провайдер недоступен",
        detail="Настроенный ИИ-провайдер временно недоступен.",
    )


def ai_model_missing() -> ApiError:
    return ApiError(
        status_code=503,
        code="ai_model_missing",
        title="ИИ-модель недоступна",
        detail="Настроенная ИИ-модель не установлена.",
    )


def ai_disabled() -> ApiError:
    return ApiError(
        status_code=503,
        code="ai_disabled",
        title="ИИ отключён",
        detail="Анализ ответов отключён в настройках приложения.",
    )


def ai_provider_timeout() -> ApiError:
    return ApiError(
        status_code=504,
        code="ai_provider_timeout",
        title="Истекло время ожидания ИИ",
        detail="ИИ-провайдер не успел ответить. Анализ можно запустить повторно.",
    )


def ai_invalid_response() -> ApiError:
    return ApiError(
        status_code=502,
        code="ai_invalid_response",
        title="Некорректный ответ ИИ",
        detail="Ответ ИИ-провайдера не прошёл проверку структуры.",
    )


def ai_request_in_progress() -> ApiError:
    return ApiError(
        status_code=409,
        code="ai_request_in_progress",
        title="Анализ уже выполняется",
        detail="Запрос с этим ключом идемпотентности ещё выполняется.",
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


def invalid_date_range(detail: str) -> ApiError:
    return ApiError(
        status_code=422,
        code="validation_error",
        title="Validation error",
        detail=detail,
    )
