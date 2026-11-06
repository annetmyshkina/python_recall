from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.core.models import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.cards.models import Card
    from backend.app.categories.models import Category


class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A knowledge topic belonging to exactly one category."""

    __tablename__ = "topics"

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_topics_name_present"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 5000",
            name="ck_topics_description_length",
        ),
        Index("ix_topics_category_id", "category_id"),
        Index(
            "uq_topics_category_name_ci",
            "category_id",
            func.lower(name),
            unique=True,
        ),
    )

    category: Mapped["Category"] = relationship(back_populates="topics")
    cards: Mapped[list["Card"]] = relationship(
        back_populates="topic",
        passive_deletes=True,
    )
