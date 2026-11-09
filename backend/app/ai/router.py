from fastapi import APIRouter

from backend.app.ai.manager import AiManager
from backend.app.ai.schemas import AiProviderResponse, AiProvidersResponse


def build_ai_router(manager: AiManager) -> APIRouter:
    """Expose diagnostics without making the core API depend on AI."""
    router = APIRouter(prefix="/ai", tags=["AI"])

    @router.get(
        "/providers",
        operation_id="list_ai_providers",
        response_model=AiProvidersResponse,
        summary="Inspect configured AI providers without affecting core health",
    )
    async def list_ai_providers() -> AiProvidersResponse:
        provider = await manager.get_status()
        return AiProvidersResponse(
            default_provider=provider.name,
            items=[
                AiProviderResponse(
                    name=provider.name,
                    enabled=provider.enabled,
                    status=provider.status,
                    model=provider.model,
                )
            ],
        )

    return router
