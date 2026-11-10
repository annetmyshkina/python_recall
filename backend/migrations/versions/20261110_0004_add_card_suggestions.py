"""Add generated card suggestions.

Revision ID: 20261110_0004
Revises: 20261109_0003
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0004"
down_revision: str | None = "20261109_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_suggestions",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_card_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "accepted",
                "rejected",
                name="card_suggestion_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
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
                name="card_suggestion_difficulty",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(question)) > 0 AND length(question) <= 10000",
            name="ck_ai_suggestions_question_length",
        ),
        sa.CheckConstraint(
            "length(btrim(answer)) > 0 AND length(answer) <= 50000",
            name="ck_ai_suggestions_answer_length",
        ),
        sa.CheckConstraint(
            "explanation IS NULL OR length(explanation) <= 50000",
            name="ck_ai_suggestions_explanation_length",
        ),
        sa.CheckConstraint(
            "code_example IS NULL OR length(code_example) <= 50000",
            name="ck_ai_suggestions_code_example_length",
        ),
        sa.CheckConstraint(
            "position >= 0 AND position < 10",
            name="ck_ai_suggestions_position_range",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND reviewed_at IS NULL "
            "AND accepted_card_id IS NULL) OR "
            "(status = 'accepted' AND reviewed_at IS NOT NULL "
            "AND accepted_card_id IS NOT NULL) OR "
            "(status = 'rejected' AND reviewed_at IS NOT NULL "
            "AND accepted_card_id IS NULL)",
            name="ck_ai_suggestions_status_fields_match",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_card_id"], ["cards.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["ai_requests.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "accepted_card_id", name="uq_ai_suggestions_accepted_card_id"
        ),
        sa.UniqueConstraint(
            "request_id", "position", name="uq_ai_suggestions_request_position"
        ),
    )
    op.create_index(
        "ix_ai_suggestions_request_id",
        "ai_suggestions",
        ["request_id"],
    )
    op.create_index(
        "ix_ai_suggestions_status_created",
        "ai_suggestions",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_ai_suggestions_topic_status_created",
        "ai_suggestions",
        ["topic_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("ai_suggestions")
