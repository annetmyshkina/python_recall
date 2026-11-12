import pytest

from backend.app.ai.scenarios.language import require_russian_text


def test_require_russian_text_accepts_russian_prose() -> None:
    assert require_russian_text("Используйте functools.wraps.") == (
        "Используйте functools.wraps."
    )


def test_require_russian_text_rejects_english_prose() -> None:
    with pytest.raises(ValueError, match="Russian"):
        require_russian_text("Use functools.wraps.")
