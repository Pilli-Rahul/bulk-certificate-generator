"""Background job processing."""

import logging
from datetime import datetime

from app.config import get_settings
from app.database import SessionLocal
from app.models import Certificate, Job
from app.services.certificate_generator import generate_certificate_pdf
from app.services.job_service import certificate_file_path, refresh_job_status

logger = logging.getLogger(__name__)


def process_job(job_id: str) -> None:
    """Process pending certificates independently using a worker-owned session."""
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Job %s no longer exists", job_id)
            return
        job.status = "processing"
        job.started_at = job.started_at or datetime.utcnow()
        db.commit()
        certificates = list(
            db.query(Certificate).filter(Certificate.job_id == job_id, Certificate.status == "pending").all()
        )
        settings = get_settings()
        for certificate in certificates:
            try:
                output_path = certificate_file_path(settings, job_id, certificate.id)
                generate_certificate_pdf(
                    output_path,
                    certificate_title=job.certificate_title,
                    event_name=job.event_name,
                    issued_by=job.issued_by,
                    issue_date=job.issue_date.isoformat(),
                    recipient_name=certificate.recipient_name or "",
                    certificate_id=certificate.id,
                )
                certificate.status = "success"
                certificate.file_path = str(output_path)
                certificate.generated_at = datetime.utcnow()
                logger.info("Generated certificate %s for job %s", certificate.id, job_id)
            except Exception as exc:  # Each certificate must be isolated from the next one.
                certificate.status = "failed"
                certificate.error_message = str(exc)[:1000] or "Certificate generation failed."
                logger.exception("Certificate %s failed", certificate.id)
            db.commit()
        refresh_job_status(db, job)
    except Exception:
        logger.exception("Job %s failed unexpectedly", job_id)
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def recover_processing_jobs() -> list[str]:
    """Reset interrupted processing jobs so startup can queue them again."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.status == "processing").all()
        job_ids = [job.id for job in jobs]
        for job in jobs:
            job.status = "pending"
            job.started_at = None
        db.commit()
        return job_ids
    finally:
        db.close()
