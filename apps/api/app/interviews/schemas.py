"""Public minimum projections for scheduled interviews."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobDescriptionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1, max_length=200)


class CandidateInterviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID
    job_description: JobDescriptionSummary = Field(alias="jobDescription")
    scheduled_at: datetime = Field(alias="scheduledAt")
    status: str


class CandidateInterviewPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[CandidateInterviewResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")


class CandidateSelectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID
    display_name: str = Field(alias="displayName", min_length=1, max_length=200)
    email: str


class ManagerCandidatePage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[CandidateSelectionResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")


class ScheduleInterviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidateId: UUID
    jobDescriptionId: UUID
    scheduledAt: datetime


class ManagerInterviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID
    candidate: CandidateSelectionResponse
    job_description: JobDescriptionSummary = Field(alias="jobDescription")
    scheduled_at: datetime = Field(alias="scheduledAt")
    status: str


class ManagerInterviewPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ManagerInterviewResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")
