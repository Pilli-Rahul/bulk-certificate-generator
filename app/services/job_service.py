"""Database operations and status calculations for jobs."""

import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Certificate, Job
from app.schemas import JobCreate

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_recipient(name: str | None, email: str | None) -> str | None:
    """Return a clear validation error, or None when a recipient is valid."""
    if not name:
        return "Name is required."
    if not 1 <= len(name) <= 100:
        return "Name must be between 1 and 100 characters."
    if not email or not EMAIL_RE.fullmatch(email):
        return "A valid email address is required."
    return None


def create_job(db: Session, payload: JobCreate, settings: Settings) -> Job:
    """Create a job and one certificate row for every submitted recipient."""
    job = Job(
        certificate_title=payload.certificate_title,
        event_name=payload.event_name,
        issued_by=payload.issued_by,
        issue_date=payload.issue_date,
        total=len(payload.recipients),
        status="pending",
    )
    db.add(job)
    db.flush()
    seen_emails: set[str] = set()
    for recipient in payload.recipients:
        name = recipient.name
        email = recipient.email
        error = validate_recipient(name, email)
        normalized_email = email.lower() if email else None
        if error is None and normalized_email in seen_emails:
            error = "Duplicate email address in this job."
        if normalized_email:
            seen_emails.add(normalized_email)
        db.add(
            Certificate(
                job_id=job.id,
                recipient_name=name,
                recipient_email=email,
                status="failed" if error else "pending",
                error_message=error,
            )
        )
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: str) -> Job | None:
    """Find a job by ID."""
    return db.get(Job, job_id)


def calculate_counts(db: Session, job_id: str) -> dict[str, int]:
    """Count certificates by status for one job."""
    rows = db.execute(
        select(Certificate.status, func.count(Certificate.id)).where(Certificate.job_id == job_id).group_by(Certificate.status)
    ).all()
    counts = {"success": 0, "failed": 0, "pending": 0}
    for status, count in rows:
        counts[status] = count
    return counts


def refresh_job_status(db: Session, job: Job) -> None:
    """Set the final status when no pending certificate remains."""
    counts = calculate_counts(db, job.id)
    if counts["pending"]:
        return
    if counts["success"] == job.total:
        job.status = "completed"
    elif counts["success"]:
        job.status = "completed_with_errors"
    else:
        job.status = "failed"
    job.completed_at = datetime.utcnow()
    db.commit()


def certificate_file_path(settings: Settings, job_id: str, certificate_id: str) -> Path:
    """Build a safe storage path using generated UUIDs only."""
    return Path(settings.storage_path) / job_id / f"{certificate_id}.pdf"
