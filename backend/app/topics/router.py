from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from backend.app.core.dependencies import SessionDependency
from backend.app.topics import service
from backend.app.topics.schemas import TopicCreate, TopicPage, TopicPatch, TopicRead

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get("", operation_id="list_topics", response_model=TopicPage)
async def list_topics(
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category_id: UUID | None = None,
) -> TopicPage:
    return service.list_topics(
        session,
        page=page,
        limit=limit,
        category_id=category_id,
    )


@router.post(
    "",
    operation_id="create_topic",
    response_model=TopicRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(
    payload: TopicCreate,
    response: Response,
    session: SessionDependency,
) -> TopicRead:
    topic = service.create_topic(session, payload)
    response.headers["Location"] = f"/api/v1/topics/{topic.id}"
    return TopicRead.model_validate(topic)


@router.get("/{topic_id}", operation_id="get_topic", response_model=TopicRead)
async def get_topic(topic_id: UUID, session: SessionDependency) -> TopicRead:
    return TopicRead.model_validate(service.get_topic(session, topic_id))


@router.patch("/{topic_id}", operation_id="update_topic", response_model=TopicRead)
async def update_topic(
    topic_id: UUID,
    payload: TopicPatch,
    session: SessionDependency,
) -> TopicRead:
    return TopicRead.model_validate(service.update_topic(session, topic_id, payload))


@router.delete(
    "/{topic_id}",
    operation_id="delete_topic",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_topic(topic_id: UUID, session: SessionDependency) -> None:
    service.delete_topic(session, topic_id)
