from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.categories.models import Category
from backend.app.categories.schemas import CategoryCreate, CategoryPage, CategoryPatch
from backend.app.core.exceptions import (
    deletion_restricted,
    duplicate_resource,
    resource_not_found,
)
from backend.app.core.pagination import build_pagination
from backend.app.topics.models import Topic


def list_categories(session: Session, *, page: int, limit: int) -> CategoryPage:
    total = session.scalar(select(func.count()).select_from(Category)) or 0
    categories = session.scalars(
        select(Category)
        .order_by(Category.name.asc(), Category.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return CategoryPage(
        items=list(categories),
        pagination=build_pagination(page=page, limit=limit, total=total),
    )


def get_category(session: Session, category_id: UUID) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise resource_not_found("Category")
    return category


def create_category(session: Session, payload: CategoryCreate) -> Category:
    category = Category(**payload.model_dump())
    session.add(category)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise duplicate_resource("Category") from error
    session.refresh(category)
    return category


def update_category(
    session: Session, category_id: UUID, payload: CategoryPatch
) -> Category:
    category = get_category(session, category_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise duplicate_resource("Category") from error
    session.refresh(category)
    return category


def delete_category(session: Session, category_id: UUID) -> None:
    category = get_category(session, category_id)
    has_topics = session.scalar(
        select(Topic.id).where(Topic.category_id == category_id).limit(1)
    )
    if has_topics is not None:
        raise deletion_restricted("Category contains topics and cannot be deleted.")
    session.delete(category)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise deletion_restricted(
            "Category contains topics and cannot be deleted."
        ) from error
