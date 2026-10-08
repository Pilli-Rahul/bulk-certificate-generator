"""Pydantic request and response schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipientInput(BaseModel):
    """Raw recipient data; detailed validation is intentionally per-recipient."""

    name: str | None = None
    email: str | None = None

    @field_validator("name", "email", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class JobCreate(BaseModel):
    """Top-level bulk job request."""

    certificate_title: str = Field(min_length=1, max_length=255)
    event_name: str = Field(min_length=1, max_length=255)
    issued_by: str = Field(min_length=1, max_length=255)
    issue_date: date
    recipients: list[RecipientInput] = Field(min_length=1)

    @field_validator("certificate_title", "event_name", "issued_by", mode="before")
    @classmethod
    def trim_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class LinkSet(BaseModel):
    """Links returned for a job."""

    self: str
    download: str


class JobCreated(BaseModel):
    """Accepted job response."""

    job_id: str
    status: str
    total: int
    links: LinkSet


CertificateStatus = Literal["pending", "success", "failed"]
JobStatus = Literal["pending", "processing", "completed", "completed_with_errors", "failed"]


class CertificateResult(BaseModel):
    """Public state of one certificate."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None = None
    email: str | None = None
    status: CertificateStatus
    error_message: str | None = None
    download_url: str | None = None


class JobStatusResponse(BaseModel):
    """Detailed job status and paginated certificate results."""

    job_id: str
    status: JobStatus
    certificate_title: str
    event_name: str
    issued_by: str
    issue_date: date
    total: int
    succeeded: int
    failed: int
    pending: int
    progress_percent: float
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    certificates: list[CertificateResult]
    limit: int
    offset: int
