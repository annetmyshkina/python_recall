import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.main import create_app


def build_test_app(database: Database | None = None) -> FastAPI:
    settings = Settings(
        _env_file=None,
        app_env="test",
        app_service="python-recall-backend",
        app_version="0.1.0",
        database_url="sqlite+pysqlite:///:memory:",
    )
    return create_app(settings, database)


class UnavailableDatabase(Database):
    """Database double that fails without exposing connection details."""

    def check_connection(self) -> None:
        raise OperationalError("SELECT 1", {}, RuntimeError("database is down"))


@pytest.mark.asyncio
async def test_health_reports_backend_liveness() -> None:
    transport = httpx.ASGITransport(app=build_test_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "status": "ok",
        "service": "python-recall-backend",
        "version": "0.1.0",
    }


@pytest.mark.asyncio
async def test_generated_openapi_contains_health_operation() -> None:
    transport = httpx.ASGITransport(app=build_test_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    document = response.json()
    operation = document["paths"]["/api/v1/health"]["get"]
    assert operation["operationId"] == "get_health"
    assert operation["tags"] == ["Health"]

    database_operation = document["paths"]["/api/v1/health/database"]["get"]
    assert database_operation["operationId"] == "get_database_health"
    assert database_operation["tags"] == ["Health"]


@pytest.mark.asyncio
async def test_database_health_reports_available_database() -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    transport = httpx.ASGITransport(app=build_test_app(database))
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/database")
    database.dispose()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_database_health_hides_internal_connection_error() -> None:
    database = UnavailableDatabase("sqlite+pysqlite:///:memory:")
    transport = httpx.ASGITransport(app=build_test_app(database))
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/database")
    database.dispose()

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    problem = response.json()
    assert problem["code"] == "database_unavailable"
    assert problem["instance"] == "/api/v1/health/database"
    assert problem["errors"] == []
    assert len(problem["trace_id"]) == 32
    assert "database is down" not in response.text


@pytest.mark.asyncio
async def test_framework_http_errors_use_problem_details(
    api_client: httpx.AsyncClient,
) -> None:
    missing = await api_client.get("/api/v1/not-an-endpoint")
    wrong_method = await api_client.put("/api/v1/health")

    assert missing.status_code == 404
    assert missing.headers["content-type"] == "application/problem+json"
    assert missing.json()["code"] == "resource_not_found"
    assert wrong_method.status_code == 405
    assert wrong_method.headers["content-type"] == "application/problem+json"
    assert wrong_method.json()["code"] == "method_not_allowed"


@pytest.mark.asyncio
async def test_json_body_larger_than_one_mib_is_rejected(
    api_client: httpx.AsyncClient,
) -> None:
    async def oversized_body():
        yield b'{"name":"'
        yield b"x" * (1024 * 1024)
        yield b'"}'

    response = await api_client.post(
        "/api/v1/categories",
        content=oversized_body(),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "request_too_large"
