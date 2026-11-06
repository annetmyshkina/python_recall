from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.core.models import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.cards.models import Card


class Tag(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Case-insensitive label attached to cards."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_tags_name_present"),
        Index("uq_tags_name_ci", func.lower(name), unique=True),
    )

    card_links: Mapped[list["CardTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CardTag(Base):
    """Technical many-to-many link between a card and a tag."""

    __tablename__ = "card_tags"

    card_id: Mapped[UUID] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    card: Mapped["Card"] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(back_populates="card_links")
