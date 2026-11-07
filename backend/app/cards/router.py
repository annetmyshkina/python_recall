from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from backend.app.cards import service
from backend.app.cards.models import CardDifficulty
from backend.app.cards.schemas import CardCreate, CardPage, CardPatch, CardRead
from backend.app.core.dependencies import SessionDependency

router = APIRouter(prefix="/cards", tags=["Cards"])


@router.get("", operation_id="list_cards", response_model=CardPage)
async def list_cards(
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    topic_id: UUID | None = None,
    category_id: UUID | None = None,
    tag: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    difficulty: CardDifficulty | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_archived: bool = False,
) -> CardPage:
    return service.list_cards(
        session,
        page=page,
        limit=limit,
        topic_id=topic_id,
        category_id=category_id,
        tag=tag,
        difficulty=difficulty,
        search=search,
        is_archived=is_archived,
    )


@router.post(
    "",
    operation_id="create_card",
    response_model=CardRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_card(
    payload: CardCreate,
    response: Response,
    session: SessionDependency,
) -> CardRead:
    card = service.create_card(session, payload)
    response.headers["Location"] = f"/api/v1/cards/{card.id}"
    return CardRead.model_validate(card)


@router.get("/{card_id}", operation_id="get_card", response_model=CardRead)
async def get_card(card_id: UUID, session: SessionDependency) -> CardRead:
    return CardRead.model_validate(service.get_card(session, card_id))


@router.patch("/{card_id}", operation_id="update_card", response_model=CardRead)
async def update_card(
    card_id: UUID,
    payload: CardPatch,
    session: SessionDependency,
) -> CardRead:
    return CardRead.model_validate(service.update_card(session, card_id, payload))


@router.delete(
    "/{card_id}",
    operation_id="delete_card",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_card(card_id: UUID, session: SessionDependency) -> None:
    service.delete_card(session, card_id)
