from sqlalchemy import CheckConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.app.core.database import Base
from backend.app.models import CardDifficulty, ReviewRating

EXPECTED_CORE_TABLES = {
    "answer_attempts",
    "card_tags",
    "cards",
    "categories",
    "review_logs",
    "tags",
    "topics",
}


def test_metadata_contains_only_release_1_core_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_CORE_TABLES


def test_all_tables_compile_for_postgresql() -> None:
    dialect = postgresql.dialect()

    for table in Base.metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=dialect))
        for index in table.indexes:
            assert str(CreateIndex(index).compile(dialect=dialect))


def test_foreign_keys_enforce_documented_delete_rules() -> None:
    expected = {
        ("topics", "category_id"): "RESTRICT",
        ("cards", "topic_id"): "RESTRICT",
        ("card_tags", "card_id"): "CASCADE",
        ("card_tags", "tag_id"): "CASCADE",
        ("answer_attempts", "card_id"): "RESTRICT",
        ("review_logs", "card_id"): "RESTRICT",
        ("review_logs", "answer_attempt_id"): "RESTRICT",
    }

    actual = {}
    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            actual[(table.name, foreign_key.parent.name)] = foreign_key.ondelete

    assert actual == expected


def test_review_log_has_sm2_and_idempotency_guards() -> None:
    table = Base.metadata.tables["review_logs"]
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes}

    assert "ck_review_logs_rating_quality_match" in check_names
    assert "ck_review_logs_ease_factors_minimum" in check_names
    assert "uq_review_logs_idempotency_key" in index_names


def test_domain_enums_match_public_api_values() -> None:
    assert [difficulty.value for difficulty in CardDifficulty] == [
        "beginner",
        "intermediate",
        "advanced",
    ]
    assert [rating.value for rating in ReviewRating] == [
        "again",
        "hard",
        "good",
        "easy",
    ]
