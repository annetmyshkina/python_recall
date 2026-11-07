from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from backend.app.core.schemas import ApiSchema, Page
from backend.app.core.validation import normalize_name


class CategoryCreate(ApiSchema):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)

    _normalize_name = field_validator("name")(normalize_name)


class CategoryPatch(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Name must not be null.")
        return normalize_name(value)

    @model_validator(mode="after")
    def require_field(self) -> "CategoryPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class CategoryRead(ApiSchema):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class CategoryPage(Page[CategoryRead]):
    pass
