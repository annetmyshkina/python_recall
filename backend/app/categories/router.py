from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from backend.app.categories import service
from backend.app.categories.schemas import (
    CategoryCreate,
    CategoryPage,
    CategoryPatch,
    CategoryRead,
)
from backend.app.core.dependencies import SessionDependency

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", operation_id="list_categories", response_model=CategoryPage)
async def list_categories(
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CategoryPage:
    return service.list_categories(session, page=page, limit=limit)


@router.post(
    "",
    operation_id="create_category",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreate,
    response: Response,
    session: SessionDependency,
) -> CategoryRead:
    category = service.create_category(session, payload)
    response.headers["Location"] = f"/api/v1/categories/{category.id}"
    return CategoryRead.model_validate(category)


@router.get("/{category_id}", operation_id="get_category", response_model=CategoryRead)
async def get_category(category_id: UUID, session: SessionDependency) -> CategoryRead:
    return CategoryRead.model_validate(service.get_category(session, category_id))


@router.patch(
    "/{category_id}", operation_id="update_category", response_model=CategoryRead
)
async def update_category(
    category_id: UUID,
    payload: CategoryPatch,
    session: SessionDependency,
) -> CategoryRead:
    return CategoryRead.model_validate(
        service.update_category(session, category_id, payload)
    )


@router.delete(
    "/{category_id}",
    operation_id="delete_category",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_category(category_id: UUID, session: SessionDependency) -> None:
    service.delete_category(session, category_id)
