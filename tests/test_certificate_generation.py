from pathlib import Path

from app.services.certificate_generator import generate_certificate_pdf


def test_pdf_is_created_for_unicode_and_long_name(tmp_path: Path) -> None:
    output = generate_certificate_pdf(
        tmp_path / "certificate.pdf",
        certificate_title="Completion & Achievement",
        event_name="Python <Bootcamp>",
        issued_by="ABC > Organization",
        issue_date="2026-10-08",
        recipient_name="José Very Long Recipient Name With Many Characters To Fit",
        certificate_id="certificate-id",
    )
    content = output.read_bytes()
    assert output.exists()
    assert content.startswith(b"%PDF")
    assert len(content) > 100
