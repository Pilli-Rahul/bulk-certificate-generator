"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import create_tables
from app.routers.jobs import router as jobs_router
from app.services.worker import process_job, recover_processing_jobs

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Bulk Certificate Generator", version="1.0.0")
app.include_router(jobs_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation errors in the common API envelope."""
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed.", "details": exc.errors()}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return endpoint errors in the same envelope as validation errors."""
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Prevent internal details from leaking through the API."""
    logging.getLogger(__name__).exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "Internal server error."}})


@app.on_event("startup")
def startup() -> None:
    """Create tables and re-queue jobs interrupted by a prior process."""
    create_tables()
    for job_id in recover_processing_jobs():
        # Startup work is still dispatched through FastAPI's simple task mechanism in normal requests.
        process_job(job_id)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight liveness response."""
    return {"status": "ok"}
