def normalize_name(value: str) -> str:
    """Trim and reject an empty human-readable resource name."""
    value = value.strip()
    if not value:
        raise ValueError("Name must not be empty.")
    return value
