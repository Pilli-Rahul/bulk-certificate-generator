import io
import zipfile

from tests.test_create_job import payload


def test_single_and_zip_downloads(client) -> None:
    created = client.post("/api/v1/jobs", json=payload()).json()
    job_id = created["job_id"]
    status = client.get(f"/api/v1/jobs/{job_id}").json()
    certificate_id = status["certificates"][0]["id"]
    single = client.get(f"/api/v1/jobs/{job_id}/certificates/{certificate_id}/download")
    assert single.status_code == 200
    assert single.headers["content-type"] == "application/pdf"
    assert single.content.startswith(b"%PDF")
    archive = client.get(f"/api/v1/jobs/{job_id}/download")
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as zip_file:
        assert len(zip_file.namelist()) == 2
        assert all(name.endswith(".pdf") for name in zip_file.namelist())


def test_not_found_and_not_ready_downloads(client) -> None:
    assert client.get("/api/v1/jobs/unknown").status_code == 404
    assert client.get("/api/v1/jobs/unknown/download").status_code == 404
    data = payload()
    data["recipients"] = [{"name": "", "email": "bad"}]
    created = client.post("/api/v1/jobs", json=data).json()
    job_id = created["job_id"]
    certificate_id = client.get(f"/api/v1/jobs/{job_id}").json()["certificates"][0]["id"]
    assert client.get(f"/api/v1/jobs/{job_id}/certificates/{certificate_id}/download").status_code == 409
    assert client.get(f"/api/v1/jobs/{job_id}/download").status_code == 409
