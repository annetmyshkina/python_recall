import httpx
import pytest
from fastapi import FastAPI

from backend.app.core.config import Settings
from backend.app.main import create_app


def build_test_app() -> FastAPI:
    settings = Settings(
        _env_file=None,
        app_env="test",
        app_service="python-recall-backend",
        app_version="0.1.0",
    )
    return create_app(settings)


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
