"""Documents to upload, made here: a real text PDF (apply's own renderer), a .docx file, and a scan's PDF."""

import io
import zipfile

RESUME = """# Sam Rai
sam@example.com · Kathmandu

## Experience
### Backend Engineer, Himal Tech (2019–2025)
- Built Django REST APIs on PostgreSQL
- Moved slow work to Celery

## Education
BE Computer Engineering, Example University, 2018

## Skills
Python, Django, PostgreSQL, Celery
"""


def resume_pdf(markdown: str = RESUME) -> bytes:
    from apply.libs.render import default_template, render_html, render_pdf

    page = render_html(markdown, template=default_template("sections"), title="Sam Rai - Resume", description="")
    return render_pdf(page, paper="a4")


def docx(paragraphs: list[tuple[str, bool]], *, extra_xml: bytes = b"") -> bytes:
    """A minimal .docx: (text, is a bullet) per paragraph."""
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(
        f"<w:p>{'<w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr>' if bullet else ''}"
        f"<w:r><w:t>{text}</w:t></w:r></w:p>"
        for text, bullet in paragraphs
    )
    xml = extra_xml + f'<?xml version="1.0"?><w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>'.encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", xml)
    return out.getvalue()


def scan_pdf() -> bytes:
    """A page with nothing on it but (in a real scan) an image: no text to read."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
