from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.exceptions import ApiError, database_unavailable
from backend.app.core.schemas import ProblemDetails, ProblemField


def problem_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    errors: list[ProblemField] | None = None,
) -> JSONResponse:
    """Build one non-leaking application/problem+json response."""
    problem = ProblemDetails(
        type=f"urn:python-recall:error:{code.replace('_', '-')}",
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        code=code,
        trace_id=uuid4().hex,
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
    )


def install_exception_handlers(application: FastAPI) -> None:
    """Install the error contract once for every feature router."""

    @application.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return problem_response(
            request,
            status_code=error.status_code,
            code=error.code,
            title=error.title,
            detail=error.detail,
            errors=error.errors,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        malformed = any(item["type"] == "json_invalid" for item in error.errors())
        fields = [
            ProblemField(
                field=".".join(str(part) for part in item["loc"]),
                code=item["type"],
                message=item["msg"],
            )
            for item in error.errors()
        ]
        if malformed:
            return problem_response(
                request,
                status_code=400,
                code="malformed_request",
                title="Malformed request",
                detail="Request body is not valid JSON.",
                errors=fields,
            )
        return problem_response(
            request,
            status_code=422,
            code="validation_error",
            title="Validation error",
            detail="Request fields did not pass validation.",
            errors=fields,
        )

    @application.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request, _: SQLAlchemyError
    ) -> JSONResponse:
        error = database_unavailable()
        return problem_response(
            request,
            status_code=error.status_code,
            code=error.code,
            title=error.title,
            detail=error.detail,
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        if error.status_code == 404:
            return problem_response(
                request,
                status_code=404,
                code="resource_not_found",
                title="Resource not found",
                detail="Requested API endpoint was not found.",
            )
        if error.status_code == 405:
            return problem_response(
                request,
                status_code=405,
                code="method_not_allowed",
                title="Method not allowed",
                detail="HTTP method is not supported for this endpoint.",
            )
        return problem_response(
            request,
            status_code=error.status_code,
            code="http_error",
            title="HTTP error",
            detail="The HTTP request could not be processed.",
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _: Exception) -> JSONResponse:
        return problem_response(
            request,
            status_code=500,
            code="internal_error",
            title="Internal server error",
            detail="An unexpected error occurred.",
        )
