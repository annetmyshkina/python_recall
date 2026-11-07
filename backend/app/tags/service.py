from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import duplicate_resource, resource_not_found
from backend.app.core.pagination import build_pagination
from backend.app.tags.models import Tag
from backend.app.tags.schemas import TagCreate, TagPage, TagPatch


def list_tags(session: Session, *, page: int, limit: int) -> TagPage:
    total = session.scalar(select(func.count()).select_from(Tag)) or 0
    tags = session.scalars(
        select(Tag)
        .order_by(Tag.name.asc(), Tag.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return TagPage(
        items=list(tags),
        pagination=build_pagination(page=page, limit=limit, total=total),
    )


def get_tag(session: Session, tag_id: UUID) -> Tag:
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise resource_not_found("Tag")
    return tag


def create_tag(session: Session, payload: TagCreate) -> Tag:
    tag = Tag(**payload.model_dump())
    session.add(tag)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise duplicate_resource("Tag") from error
    session.refresh(tag)
    return tag


def update_tag(session: Session, tag_id: UUID, payload: TagPatch) -> Tag:
    tag = get_tag(session, tag_id)
    tag.name = payload.name
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise duplicate_resource("Tag") from error
    session.refresh(tag)
    return tag


def delete_tag(session: Session, tag_id: UUID) -> None:
    tag = get_tag(session, tag_id)
    session.delete(tag)
    session.commit()
