from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from backend.app.core.schemas import ApiSchema, Page
from backend.app.core.validation import normalize_name


class TagCreate(ApiSchema):
    name: str = Field(min_length=1, max_length=50)

    _normalize_name = field_validator("name")(normalize_name)


class TagPatch(TagCreate):
    pass


class TagRead(ApiSchema):
    id: UUID
    name: str
    created_at: datetime


class TagPage(Page[TagRead]):
    pass
