from math import ceil

from backend.app.core.schemas import Pagination


def build_pagination(*, page: int, limit: int, total: int) -> Pagination:
    """Calculate stable page metadata, including zero pages for an empty list."""
    return Pagination(
        page=page,
        limit=limit,
        total=total,
        pages=ceil(total / limit) if total else 0,
    )
