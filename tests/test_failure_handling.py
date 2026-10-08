from tests.test_create_job import payload


def test_one_generator_failure_does_not_stop_other_certificates(client, monkeypatch) -> None:
    from app.services import worker

    original = worker.generate_certificate_pdf

    def fail_one(output_path, **kwargs):
        if kwargs["recipient_name"] == "Break Me":
            raise RuntimeError("simulated generator failure")
        return original(output_path, **kwargs)

    monkeypatch.setattr(worker, "generate_certificate_pdf", fail_one)
    data = payload()
    data["recipients"] = [
        {"name": "Works", "email": "works@example.com"},
        {"name": "Break Me", "email": "break@example.com"},
    ]
    created = client.post("/api/v1/jobs", json=data).json()
    body = client.get(f"/api/v1/jobs/{created['job_id']}").json()
    assert body["status"] == "completed_with_errors"
    assert body["succeeded"] == 1
    assert body["failed"] == 1
    failed = next(item for item in body["certificates"] if item["status"] == "failed")
    assert "simulated generator failure" in failed["error_message"]
