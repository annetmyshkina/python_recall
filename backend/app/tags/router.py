from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from backend.app.core.dependencies import SessionDependency
from backend.app.tags import service
from backend.app.tags.schemas import TagCreate, TagPage, TagPatch, TagRead

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", operation_id="list_tags", response_model=TagPage)
async def list_tags(
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TagPage:
    return service.list_tags(session, page=page, limit=limit)


@router.post(
    "",
    operation_id="create_tag",
    response_model=TagRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    payload: TagCreate,
    response: Response,
    session: SessionDependency,
) -> TagRead:
    tag = service.create_tag(session, payload)
    response.headers["Location"] = f"/api/v1/tags/{tag.id}"
    return TagRead.model_validate(tag)


@router.get("/{tag_id}", operation_id="get_tag", response_model=TagRead)
async def get_tag(tag_id: UUID, session: SessionDependency) -> TagRead:
    return TagRead.model_validate(service.get_tag(session, tag_id))


@router.patch("/{tag_id}", operation_id="update_tag", response_model=TagRead)
async def update_tag(
    tag_id: UUID,
    payload: TagPatch,
    session: SessionDependency,
) -> TagRead:
    return TagRead.model_validate(service.update_tag(session, tag_id, payload))


@router.delete(
    "/{tag_id}",
    operation_id="delete_tag",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tag(tag_id: UUID, session: SessionDependency) -> None:
    service.delete_tag(session, tag_id)
