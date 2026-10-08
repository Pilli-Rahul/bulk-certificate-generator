"""Pure PDF certificate generation logic."""

from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)


def _font_name() -> str:
    """Register a broadly available Unicode font, falling back to Helvetica."""
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for font_path in candidates:
        if font_path.is_file():
            name = "CertificateUnicodeFont"
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(font_path)))
            return name
    return "Helvetica"


def _fit_font_size(text: str, font_name: str, max_size: int, max_width: float) -> int:
    """Return the largest font size that fits within the available width."""
    for size in range(max_size, 11, -1):
        if stringWidth(text, font_name, size) <= max_width:
            return size
    return 11


def generate_certificate_pdf(
    output_path: str | Path,
    *,
    certificate_title: str,
    event_name: str,
    issued_by: str,
    issue_date: str,
    recipient_name: str,
    certificate_id: str,
) -> Path:
    """Generate one predefined A4 landscape certificate and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    canvas = Canvas(str(path), pagesize=landscape(A4))
    font_name = _font_name()
    canvas.setTitle(certificate_title)
    margin = 28
    canvas.setStrokeColorRGB(0.12, 0.23, 0.34)
    canvas.setLineWidth(3)
    canvas.rect(margin, margin, PAGE_WIDTH - 2 * margin, PAGE_HEIGHT - 2 * margin)
    canvas.setLineWidth(1)
    canvas.rect(margin + 9, margin + 9, PAGE_WIDTH - 2 * margin - 18, PAGE_HEIGHT - 2 * margin - 18)

    canvas.setFillColorRGB(0.12, 0.23, 0.34)
    canvas.setFont(font_name, 30)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 105, certificate_title)
    canvas.setFillColorRGB(0.2, 0.2, 0.2)
    canvas.setFont(font_name, 16)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 155, "This is to certify that")

    name_size = _fit_font_size(recipient_name, font_name, 34, PAGE_WIDTH - 150)
    canvas.setFillColorRGB(0.07, 0.12, 0.17)
    canvas.setFont(font_name, name_size)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 + 25, recipient_name)

    canvas.setFillColorRGB(0.2, 0.2, 0.2)
    canvas.setFont(font_name, 15)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 - 20, f"for successfully completing {event_name}")
    canvas.setFont(font_name, 13)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 - 52, f"Issued by: {issued_by}    |    Date: {issue_date}")

    canvas.setFont(font_name, 9)
    canvas.drawString(margin + 18, margin + 17, f"Certificate ID: {certificate_id}")
    canvas.save()
    return path
