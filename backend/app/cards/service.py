from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.app.cards.models import Card, CardDifficulty
from backend.app.cards.schemas import CardCreate, CardPage, CardPatch
from backend.app.core.exceptions import deletion_restricted, resource_not_found
from backend.app.core.pagination import build_pagination
from backend.app.reviews.models import AnswerAttempt, ReviewLog
from backend.app.tags.models import CardTag, Tag
from backend.app.topics.models import Topic

CARD_LOAD_OPTIONS = (selectinload(Card.tag_links).selectinload(CardTag.tag),)


def get_card(session: Session, card_id: UUID) -> Card:
    card = session.scalar(
        select(Card).where(Card.id == card_id).options(*CARD_LOAD_OPTIONS)
    )
    if card is None:
        raise resource_not_found("Card")
    return card


def require_topic(session: Session, topic_id: UUID) -> None:
    if session.get(Topic, topic_id) is None:
        raise resource_not_found("Topic")


def load_tags(session: Session, tag_ids: list[UUID]) -> list[Tag]:
    if not tag_ids:
        return []
    tags = session.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()
    by_id = {tag.id: tag for tag in tags}
    if len(by_id) != len(tag_ids):
        raise resource_not_found("Tag")
    return [by_id[tag_id] for tag_id in tag_ids]


def list_cards(
    session: Session,
    *,
    page: int,
    limit: int,
    topic_id: UUID | None,
    category_id: UUID | None,
    tag: str | None,
    difficulty: CardDifficulty | None,
    search: str | None,
    is_archived: bool,
) -> CardPage:
    statement = select(Card)
    filters = [Card.is_archived.is_(is_archived)]

    if topic_id is not None:
        filters.append(Card.topic_id == topic_id)
    if category_id is not None:
        statement = statement.join(Topic, Card.topic_id == Topic.id)
        filters.append(Topic.category_id == category_id)
    if tag is not None:
        statement = statement.join(CardTag, CardTag.card_id == Card.id).join(
            Tag, Tag.id == CardTag.tag_id
        )
        filters.append(func.lower(Tag.name) == tag.strip().lower())
    if difficulty is not None:
        filters.append(Card.difficulty == difficulty)
    if search:
        escaped = (
            search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                Card.question.ilike(pattern, escape="\\"),
                Card.answer.ilike(pattern, escape="\\"),
                Card.explanation.ilike(pattern, escape="\\"),
            )
        )

    statement = statement.where(*filters)
    total = (
        session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    cards = session.scalars(
        statement.options(*CARD_LOAD_OPTIONS)
        .order_by(Card.created_at.desc(), Card.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return CardPage(
        items=list(cards),
        pagination=build_pagination(page=page, limit=limit, total=total),
    )


def create_card(session: Session, payload: CardCreate) -> Card:
    require_topic(session, payload.topic_id)
    tags = load_tags(session, payload.tag_ids)
    values = payload.model_dump(exclude={"tag_ids"})
    card = Card(**values)
    card.tag_links = [CardTag(tag=tag) for tag in tags]
    session.add(card)
    session.commit()
    return get_card(session, card.id)


def update_card(session: Session, card_id: UUID, payload: CardPatch) -> Card:
    card = get_card(session, card_id)
    changes = payload.model_dump(exclude_unset=True)
    tag_ids = changes.pop("tag_ids", None)

    if "topic_id" in changes:
        require_topic(session, changes["topic_id"])
    tags = load_tags(session, tag_ids) if tag_ids is not None else None

    for field, value in changes.items():
        setattr(card, field, value)
    if tags is not None:
        card.tag_links = [CardTag(tag=tag) for tag in tags]
    card.updated_at = datetime.now(UTC)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise
    return get_card(session, card_id)


def delete_card(session: Session, card_id: UUID) -> None:
    card = get_card(session, card_id)
    has_attempt = session.scalar(
        select(AnswerAttempt.id).where(AnswerAttempt.card_id == card_id).limit(1)
    )
    has_review = session.scalar(
        select(ReviewLog.id).where(ReviewLog.card_id == card_id).limit(1)
    )
    if has_attempt is not None or has_review is not None:
        raise deletion_restricted(
            "Card has learning history and cannot be deleted. Archive it instead."
        )
    session.delete(card)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise deletion_restricted(
            "Card has learning history and cannot be deleted. Archive it instead."
        ) from error
