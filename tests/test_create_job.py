from app.models import Certificate, Job


def payload() -> dict:
    return {
        "certificate_title": "Certificate of Completion",
        "event_name": "Python Bootcamp 2026",
        "issued_by": "ABC Organization",
        "issue_date": "2026-10-08",
        "recipients": [
            {"name": "Rahul Pilli", "email": "rahul@example.com"},
            {"name": "Anita Rao", "email": "anita@example.com"},
        ],
    }


def test_create_job_returns_202_and_persists_rows(client, db_session) -> None:
    response = client.post("/api/v1/jobs", json=payload())
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"]
    assert body["total"] == 2
    assert db_session.query(Job).count() == 1
    assert db_session.query(Certificate).count() == 2
