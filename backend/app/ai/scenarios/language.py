"""Small validation helpers shared by Russian-language AI scenarios."""

import re

CYRILLIC_PATTERN = re.compile("[А-Яа-яЁё]")


def require_russian_text(value: str) -> str:
    """Reject prose that contains no Russian letters at all."""
    if CYRILLIC_PATTERN.search(value) is None:
        raise ValueError("user-facing text must be written in Russian")
    return value
