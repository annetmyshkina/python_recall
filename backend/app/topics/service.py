from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.cards.models import Card
from backend.app.categories.models import Category
from backend.app.core.exceptions import (
    deletion_restricted,
    duplicate_resource,
    resource_not_found,
)
from backend.app.core.pagination import build_pagination
from backend.app.topics.models import Topic
from backend.app.topics.schemas import TopicCreate, TopicPage, TopicPatch


def list_topics(
    session: Session,
    *,
    page: int,
    limit: int,
    category_id: UUID | None,
) -> TopicPage:
    filters = [Topic.category_id == category_id] if category_id else []
    total = session.scalar(select(func.count()).select_from(Topic).where(*filters)) or 0
    topics = session.scalars(
        select(Topic)
        .where(*filters)
        .order_by(Topic.name.asc(), Topic.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return TopicPage(
        items=list(topics),
        pagination=build_pagination(page=page, limit=limit, total=total),
    )


def get_topic(session: Session, topic_id: UUID) -> Topic:
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise resource_not_found("Topic")
    return topic


def require_category(session: Session, category_id: UUID) -> None:
    if session.get(Category, category_id) is None:
        raise resource_not_found("Category")


def create_topic(session: Session, payload: TopicCreate) -> Topic:
    require_category(session, payload.category_id)
    topic = Topic(**payload.model_dump())
    session.add(topic)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise duplicate_resource("Topic") from error
    session.refresh(topic)
    return topic


def update_topic(session: Session, topic_id: UUID, payload: TopicPatch) -> Topic:
    topic = get_topic(session, topic_id)
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes:
        require_category(session, changes["category_id"])
    for field, value in changes.items():
        setattr(topic, field, value)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise duplicate_resource("Topic") from error
    session.refresh(topic)
    return topic


def delete_topic(session: Session, topic_id: UUID) -> None:
    topic = get_topic(session, topic_id)
    has_cards = session.scalar(
        select(Card.id).where(Card.topic_id == topic_id).limit(1)
    )
    if has_cards is not None:
        raise deletion_restricted("Topic contains cards and cannot be deleted.")
    session.delete(topic)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise deletion_restricted(
            "Topic contains cards and cannot be deleted."
        ) from error
