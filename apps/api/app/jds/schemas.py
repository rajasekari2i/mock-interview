"""Manager JD request and minimum response contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ManualJobDescriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)

    @field_validator("title", "content")
    @classmethod
    def nonblank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class ManagerJobDescriptionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    title: str
    source_type: str = Field(alias="sourceType")
    source_format: str | None = Field(alias="sourceFormat")
    created_at: datetime = Field(alias="createdAt")


class ManagerJobDescriptionPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ManagerJobDescriptionResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")
