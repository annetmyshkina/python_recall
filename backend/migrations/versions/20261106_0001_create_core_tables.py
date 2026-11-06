"""Create Release 1 core tables.

Revision ID: 20261106_0001
Revises: None
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261106_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "description IS NULL OR length(description) <= 5000",
            name="ck_categories_description_length",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0", name="ck_categories_name_present"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_categories_name_ci",
        "categories",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "tags",
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_tags_name_present"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_tags_name_ci",
        "tags",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "topics",
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "description IS NULL OR length(description) <= 5000",
            name="ck_topics_description_length",
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_topics_name_present"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topics_category_id", "topics", ["category_id"])
    op.create_index(
        "uq_topics_category_name_ci",
        "topics",
        ["category_id", sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "cards",
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("code_example", sa.Text(), nullable=True),
        sa.Column(
            "difficulty",
            sa.Enum(
                "beginner",
                "intermediate",
                "advanced",
                name="card_difficulty",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "repetitions", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "interval_days", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "ease_factor",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("2.50"),
            nullable=False,
        ),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(question)) > 0", name="ck_cards_question_present"
        ),
        sa.CheckConstraint(
            "length(question) <= 10000", name="ck_cards_question_length"
        ),
        sa.CheckConstraint("length(btrim(answer)) > 0", name="ck_cards_answer_present"),
        sa.CheckConstraint("length(answer) <= 50000", name="ck_cards_answer_length"),
        sa.CheckConstraint(
            "explanation IS NULL OR length(explanation) <= 50000",
            name="ck_cards_explanation_length",
        ),
        sa.CheckConstraint(
            "code_example IS NULL OR length(code_example) <= 50000",
            name="ck_cards_code_example_length",
        ),
        sa.CheckConstraint("repetitions >= 0", name="ck_cards_repetitions_nonnegative"),
        sa.CheckConstraint(
            "interval_days >= 0", name="ck_cards_interval_days_nonnegative"
        ),
        sa.CheckConstraint("ease_factor >= 1.30", name="ck_cards_ease_factor_minimum"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cards_topic_id", "cards", ["topic_id"])
    op.create_index(
        "ix_cards_review_queue",
        "cards",
        ["next_review_at"],
        postgresql_where=sa.text("is_archived = false"),
    )

    op.create_table(
        "card_tags",
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("card_id", "tag_id"),
    )

    op.create_table(
        "answer_attempts",
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(user_answer)) > 0",
            name="ck_answer_attempts_user_answer_present",
        ),
        sa.CheckConstraint(
            "length(user_answer) <= 50000",
            name="ck_answer_attempts_user_answer_length",
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_answer_attempts_card_created",
        "answer_attempts",
        ["card_id", "created_at"],
    )

    op.create_table(
        "review_logs",
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("answer_attempt_id", sa.Uuid(), nullable=True),
        sa.Column(
            "rating",
            sa.Enum(
                "again",
                "hard",
                "good",
                "easy",
                name="review_rating",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("previous_repetitions", sa.Integer(), nullable=False),
        sa.Column("previous_interval_days", sa.Integer(), nullable=False),
        sa.Column(
            "previous_ease_factor",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column("previous_next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_repetitions", sa.Integer(), nullable=False),
        sa.Column("new_interval_days", sa.Integer(), nullable=False),
        sa.Column(
            "new_ease_factor",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column("new_next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quality IN (1, 3, 4, 5)", name="ck_review_logs_quality_supported"
        ),
        sa.CheckConstraint(
            "(rating = 'again' AND quality = 1) OR "
            "(rating = 'hard' AND quality = 3) OR "
            "(rating = 'good' AND quality = 4) OR "
            "(rating = 'easy' AND quality = 5)",
            name="ck_review_logs_rating_quality_match",
        ),
        sa.CheckConstraint(
            "previous_repetitions >= 0 AND new_repetitions >= 0",
            name="ck_review_logs_repetitions_nonnegative",
        ),
        sa.CheckConstraint(
            "previous_interval_days >= 0 AND new_interval_days >= 0",
            name="ck_review_logs_intervals_nonnegative",
        ),
        sa.CheckConstraint(
            "previous_ease_factor >= 1.30 AND new_ease_factor >= 1.30",
            name="ck_review_logs_ease_factors_minimum",
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_review_logs_request_fingerprint_length",
        ),
        sa.ForeignKeyConstraint(
            ["answer_attempt_id"], ["answer_attempts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "answer_attempt_id", name="uq_review_logs_answer_attempt_id"
        ),
    )
    op.create_index(
        "ix_review_logs_card_reviewed",
        "review_logs",
        ["card_id", "reviewed_at"],
    )
    op.create_index("ix_review_logs_reviewed_at", "review_logs", ["reviewed_at"])
    op.create_index(
        "uq_review_logs_idempotency_key",
        "review_logs",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("review_logs")
    op.drop_table("answer_attempts")
    op.drop_table("card_tags")
    op.drop_table("cards")
    op.drop_table("topics")
    op.drop_table("tags")
    op.drop_table("categories")
