from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.core.models import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.reviews.models import AnswerAttempt, ReviewLog
    from backend.app.tags.models import CardTag
    from backend.app.topics.models import Topic


class CardDifficulty(StrEnum):
    """Supported learner-facing card difficulty levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Card(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single learning item with its current SM-2 state."""

    __tablename__ = "cards"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(question)) > 0", name="ck_cards_question_present"
        ),
        CheckConstraint("length(question) <= 10000", name="ck_cards_question_length"),
        CheckConstraint("length(btrim(answer)) > 0", name="ck_cards_answer_present"),
        CheckConstraint("length(answer) <= 50000", name="ck_cards_answer_length"),
        CheckConstraint(
            "explanation IS NULL OR length(explanation) <= 50000",
            name="ck_cards_explanation_length",
        ),
        CheckConstraint(
            "code_example IS NULL OR length(code_example) <= 50000",
            name="ck_cards_code_example_length",
        ),
        CheckConstraint("repetitions >= 0", name="ck_cards_repetitions_nonnegative"),
        CheckConstraint(
            "interval_days >= 0", name="ck_cards_interval_days_nonnegative"
        ),
        CheckConstraint("ease_factor >= 1.30", name="ck_cards_ease_factor_minimum"),
        Index("ix_cards_topic_id", "topic_id"),
        Index(
            "ix_cards_review_queue",
            "next_review_at",
            postgresql_where=text("is_archived = false"),
        ),
    )

    topic_id: Mapped[UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[CardDifficulty] = mapped_column(
        Enum(
            CardDifficulty,
            values_callable=lambda enum: [item.value for item in enum],
            name="card_difficulty",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    repetitions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    interval_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    ease_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("2.50"),
        server_default=text("2.50"),
    )
    next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    topic: Mapped["Topic"] = relationship(back_populates="cards")
    tag_links: Mapped[list["CardTag"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    answer_attempts: Mapped[list["AnswerAttempt"]] = relationship(
        back_populates="card",
        passive_deletes=True,
    )
    review_logs: Mapped[list["ReviewLog"]] = relationship(
        back_populates="card",
        passive_deletes=True,
    )
