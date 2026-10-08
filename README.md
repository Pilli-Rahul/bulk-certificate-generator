# Bulk Certificate Generator

A small FastAPI backend that accepts one request containing many recipients, creates one PDF certificate per valid recipient, records per-recipient failures, and provides progress and download endpoints.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Python 3.11 or newer is required.

## Run

```powershell
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive Swagger documentation is at `http://127.0.0.1:8000/docs`.

## Tests

```powershell
pytest -q
```

## Example API calls

Submit a job:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/jobs `
  -H "Content-Type: application/json" `
  -d '{"certificate_title":"Certificate of Completion","event_name":"Python Bootcamp 2026","issued_by":"ABC Organization","issue_date":"2026-10-08","recipients":[{"name":"Rahul Pilli","email":"rahul@example.com"},{"name":"Anita Rao","email":"anita@example.com"}]}'
```

Check progress (replace `JOB_ID`):

```powershell
curl http://127.0.0.1:8000/api/v1/jobs/JOB_ID
```

Download one certificate (replace both IDs):

```powershell
curl -o certificate.pdf http://127.0.0.1:8000/api/v1/jobs/JOB_ID/certificates/CERTIFICATE_ID/download
```

Download all successful certificates as a ZIP:

```powershell
curl -o certificates.zip http://127.0.0.1:8000/api/v1/jobs/JOB_ID/download
```

## Design decisions

- **FastAPI:** It provides typed request validation, dependency injection, OpenAPI documentation, and simple background task support with little ceremony.
- **SQLite and SQLAlchemy:** SQLite is convenient for local development and tests. Change `DATABASE_URL` in `.env` to a SQLAlchemy URL such as `postgresql+psycopg://user:password@host/db` and install that database's driver to switch relational databases.
- **BackgroundTasks:** The API returns 202 after saving the job and schedules work after the response. This is intentionally simple and needs no extra infrastructure. Jobs can be lost if the process stops during work; production should use Celery or RQ with Redis.
- **Partial failure handling:** A malformed recipient should not discard a whole bulk request. Invalid recipients become failed certificate rows with useful messages, while valid recipients continue.
- **Per-certificate commits:** Each generated file is committed immediately so status endpoints show live progress and a later failure does not roll back earlier work.
- **Worker session:** The background worker opens and closes its own SQLAlchemy session instead of using the request session.
- **Startup recovery:** On startup, jobs left in `processing` are reset to `pending` and processed again. Pending rows are safe to retry because successful rows are skipped.
- **Security:** File names are generated UUIDs, never user input. Inputs are validated, error responses avoid internal details, and no secrets are stored in source. Authentication, authorization, rate limiting, and strict production CORS are still needed for a public deployment.

## Known limitations and production improvements

The in-process worker is not durable across crashes and does not provide distributed concurrency or retries. For production I would use Celery/RQ with Redis, object storage such as S3 for PDFs, retry policies with idempotency, authentication and authorization, rate limiting, structured logging, metrics, and database migrations. A production database should also use a proper migration tool once the schema evolves.

## How to change things

- **Change the template:** Edit `app/services/certificate_generator.py`; the function receives plain values and can be tested independently.
- **Change the batch limit:** Set `MAX_RECIPIENTS` in `.env`.
- **Change storage:** Set `STORAGE_PATH` in `.env`; a production S3 implementation would replace the local file write and download logic.
- **Swap the task queue:** Keep `create_job` and the worker's job contract, then enqueue `process_job` in Celery/RQ instead of `BackgroundTasks`.
