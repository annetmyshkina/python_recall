from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.core.models import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.topics.models import Topic


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Top-level knowledge grouping."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_categories_name_present"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 5000",
            name="ck_categories_description_length",
        ),
        Index("uq_categories_name_ci", func.lower(name), unique=True),
    )

    topics: Mapped[list["Topic"]] = relationship(
        back_populates="category",
        passive_deletes=True,
    )
