"""HTTP endpoints for certificate jobs."""

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Certificate
from app.schemas import CertificateResult, JobCreate, JobCreated, JobStatusResponse, LinkSet
from app.services.job_service import calculate_counts, create_job, get_job
from app.services.worker import process_job

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def error(code: str, message: str, http_status: int) -> HTTPException:
    """Create the API's consistent HTTP error shape."""
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


@router.post("", response_model=JobCreated, status_code=status.HTTP_202_ACCEPTED)
def submit_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreated:
    """Create a job, persist its recipients, and schedule background processing."""
    settings = get_settings()
    if len(payload.recipients) > settings.max_recipients:
        raise error("too_many_recipients", f"A maximum of {settings.max_recipients} recipients is allowed.", 422)
    job = create_job(db, payload, settings)
    background_tasks.add_task(process_job, job.id)
    return JobCreated(
        job_id=job.id,
        status=job.status,
        total=job.total,
        links=LinkSet(
            self=f"/api/v1/jobs/{job.id}",
            download=f"/api/v1/jobs/{job.id}/download",
        ),
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def read_job(
    job_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    certificate_status: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """Return counts and a paginated list of certificate results."""
    job = get_job(db, job_id)
    if job is None:
        raise error("not_found", "Job not found.", 404)
    counts = calculate_counts(db, job_id)
    query = db.query(Certificate).filter(Certificate.job_id == job_id)
    if certificate_status:
        if certificate_status not in {"pending", "success", "failed"}:
            raise error("invalid_status", "Status must be pending, success, or failed.", 422)
        query = query.filter(Certificate.status == certificate_status)
    certificates = query.order_by(Certificate.created_at, Certificate.id).offset(offset).limit(limit).all()
    results = [
        CertificateResult(
            id=certificate.id,
            name=certificate.recipient_name,
            email=certificate.recipient_email,
            status=certificate.status,
            error_message=certificate.error_message,
            download_url=(
                f"/api/v1/jobs/{job_id}/certificates/{certificate.id}/download"
                if certificate.status == "success"
                else None
            ),
        )
        for certificate in certificates
    ]
    completed = counts["success"] + counts["failed"]
    progress = round((completed / job.total) * 100, 2) if job.total else 100.0
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        certificate_title=job.certificate_title,
        event_name=job.event_name,
        issued_by=job.issued_by,
        issue_date=job.issue_date,
        total=job.total,
        succeeded=counts["success"],
        failed=counts["failed"],
        pending=counts["pending"],
        progress_percent=progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        certificates=results,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}/certificates/{certificate_id}/download")
def download_certificate(job_id: str, certificate_id: str, db: Session = Depends(get_db)) -> FileResponse:
    """Download one generated certificate."""
    certificate = (
        db.query(Certificate)
        .filter(Certificate.id == certificate_id, Certificate.job_id == job_id)
        .first()
    )
    if certificate is None:
        raise error("not_found", "Certificate not found.", 404)
    if certificate.status != "success" or not certificate.file_path:
        raise error("not_ready", "Certificate has not been generated successfully.", 409)
    path = Path(certificate.file_path)
    if not path.is_file():
        raise error("not_ready", "Certificate file is not available.", 409)
    return FileResponse(path, media_type="application/pdf", filename=f"{certificate.id}.pdf")


@router.get("/{job_id}/download")
def download_job(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """Download all successful certificates in a ZIP archive."""
    job = get_job(db, job_id)
    if job is None:
        raise error("not_found", "Job not found.", 404)
    certificates = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id, Certificate.status == "success")
        .order_by(Certificate.created_at)
        .all()
    )
    available = [certificate for certificate in certificates if certificate.file_path and Path(certificate.file_path).is_file()]
    if not available:
        raise error("not_ready", "No certificates have been generated yet.", 409)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for certificate in available:
            zip_file.write(certificate.file_path, arcname=f"{certificate.id}.pdf")
    archive.seek(0)
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.zip"'},
    )
