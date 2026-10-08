from tests.test_create_job import payload


def test_status_counts_progress_pagination_and_filter(client) -> None:
    data = payload()
    data["recipients"] = [
        {"name": "One", "email": "one@example.com"},
        {"name": "", "email": "bad@example.com"},
        {"name": "Three", "email": "three@example.com"},
    ]
    created = client.post("/api/v1/jobs", json=data).json()
    job_id = created["job_id"]
    response = client.get(f"/api/v1/jobs/{job_id}", params={"limit": 1, "offset": 1, "status": "failed"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["failed"] == 1
    assert body["succeeded"] == 2
    assert body["pending"] == 0
    assert body["progress_percent"] == 100.0
    assert body["status"] == "completed_with_errors"
    assert len(body["certificates"]) == 1
    assert body["certificates"][0]["status"] == "failed"
