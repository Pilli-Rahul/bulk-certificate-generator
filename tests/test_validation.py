from app.models import Certificate

from tests.test_create_job import payload


def test_empty_recipients_is_rejected(client) -> None:
    data = payload()
    data["recipients"] = []
    assert client.post("/api/v1/jobs", json=data).status_code == 422


def test_missing_top_level_field_is_rejected(client) -> None:
    data = payload()
    del data["event_name"]
    assert client.post("/api/v1/jobs", json=data).status_code == 422


def test_too_many_recipients_is_rejected(client) -> None:
    data = payload()
    data["recipients"] = [{"name": str(index), "email": f"{index}@example.com"} for index in range(4)]
    assert client.post("/api/v1/jobs", json=data).status_code == 422


def test_invalid_and_duplicate_recipients_are_stored_as_failed(client, db_session) -> None:
    data = payload()
    data["recipients"] = [
        {"name": "Good", "email": "good@example.com"},
        {"name": "", "email": "bad@example.com"},
        {"name": "Bad Email", "email": "not-an-email"},
    ]
    response = client.post("/api/v1/jobs", json=data)
    assert response.status_code == 202
    certificates = db_session.query(Certificate).all()
    assert sum(c.status == "failed" for c in certificates) == 2


def test_duplicate_email_is_failed(client, db_session) -> None:
    data = payload()
    data["recipients"] = [
        {"name": "First", "email": "same@example.com"},
        {"name": "Second", "email": "SAME@example.com"},
    ]
    assert client.post("/api/v1/jobs", json=data).status_code == 202
    assert db_session.query(Certificate).filter(Certificate.status == "failed").count() == 1
