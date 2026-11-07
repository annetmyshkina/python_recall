from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.core.models import CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.app.reviews.algorithms.sm2 import ReviewRating

if TYPE_CHECKING:
    from backend.app.cards.models import Card


class AnswerAttempt(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """User-written answer saved independently of a review result."""

    __tablename__ = "answer_attempts"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(user_answer)) > 0",
            name="ck_answer_attempts_user_answer_present",
        ),
        CheckConstraint(
            "length(user_answer) <= 50000",
            name="ck_answer_attempts_user_answer_length",
        ),
        Index("ix_answer_attempts_card_created", "card_id", "created_at"),
    )

    card_id: Mapped[UUID] = mapped_column(
        ForeignKey("cards.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)

    card: Mapped["Card"] = relationship(back_populates="answer_attempts")
    review_log: Mapped["ReviewLog | None"] = relationship(
        back_populates="answer_attempt",
        uselist=False,
        passive_deletes=True,
    )


class ReviewLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable fact of one learner-confirmed SM-2 transition."""

    __tablename__ = "review_logs"
    __table_args__ = (
        CheckConstraint(
            "quality IN (1, 3, 4, 5)",
            name="ck_review_logs_quality_supported",
        ),
        CheckConstraint(
            "(rating = 'again' AND quality = 1) OR "
            "(rating = 'hard' AND quality = 3) OR "
            "(rating = 'good' AND quality = 4) OR "
            "(rating = 'easy' AND quality = 5)",
            name="ck_review_logs_rating_quality_match",
        ),
        CheckConstraint(
            "previous_repetitions >= 0 AND new_repetitions >= 0",
            name="ck_review_logs_repetitions_nonnegative",
        ),
        CheckConstraint(
            "previous_interval_days >= 0 AND new_interval_days >= 0",
            name="ck_review_logs_intervals_nonnegative",
        ),
        CheckConstraint(
            "previous_ease_factor >= 1.30 AND new_ease_factor >= 1.30",
            name="ck_review_logs_ease_factors_minimum",
        ),
        CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_review_logs_request_fingerprint_length",
        ),
        UniqueConstraint("answer_attempt_id", name="uq_review_logs_answer_attempt_id"),
        Index("ix_review_logs_card_reviewed", "card_id", "reviewed_at"),
        Index("ix_review_logs_reviewed_at", "reviewed_at"),
        Index("uq_review_logs_idempotency_key", "idempotency_key", unique=True),
    )

    card_id: Mapped[UUID] = mapped_column(
        ForeignKey("cards.id", ondelete="RESTRICT"),
        nullable=False,
    )
    answer_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("answer_attempts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rating: Mapped[ReviewRating] = mapped_column(
        Enum(
            ReviewRating,
            values_callable=lambda enum: [item.value for item in enum],
            name="review_rating",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_ease_factor: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    previous_next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    new_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    new_ease_factor: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    new_next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    idempotency_key: Mapped[UUID] = mapped_column(nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    card: Mapped["Card"] = relationship(back_populates="review_logs")
    answer_attempt: Mapped[AnswerAttempt | None] = relationship(
        back_populates="review_log"
    )
