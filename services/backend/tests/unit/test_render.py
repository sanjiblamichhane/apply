"""
Documents in the person's templates: markdown into the template's parts, the defaults filled back into the
template as given (byte for byte), nothing read as HTML, and the page printed to a tagged PDF/UA-1.
"""

import io
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont
from pypdf import PdfReader

from apply.libs.render import (
    blocks,
    check_template,
    default_template,
    parts,
    render_html,
    render_pdf,
    sample,
    spans,
    with_letterhead,
)

GIVEN = Path(__file__).resolve().parents[1] / "support/templates"


def test_inline_markdown():
    assert spans("**Backend Engineer**, *Himal* `py` [site](https://x.example) [bad](javascript:alert(1))") == [
        {"s": "strong", "v": "Backend Engineer"},
        {"s": "text", "v": ", "},
        {"s": "emph", "v": "Himal"},
        {"s": "text", "v": " "},
        {"s": "text", "v": "py"},
        {"s": "text", "v": " "},
        {"s": "link", "v": "site", "href": "https://x.example"},
        {"s": "text", "v": " "},
        {"s": "text", "v": "bad"},
    ]
    assert spans("[555](tel:+15555550100) [me](mailto:me@x.example)")[0]["href"] == "tel:+15555550100"


def test_blocks_and_a_labelled_line_of_its_own():
    out = blocks("## Core Skills\n**Tools:** a, b\n**Languages:** c\n- One\n- Two\n  continued\n\n1. First\n\n---\nEnd")
    assert [b["t"] for b in out] == ["h", "p", "p", "ul", "ol", "p"]
    assert out[3]["items"][1] == [{"s": "text", "v": "Two continued"}]


@pytest.mark.parametrize(
    ("kind", "given", "title", "description"),
    [
        ("sections", "resume.html", "Lorem Ipsum - Resume",
         "Proident sunt culpa qui officia deserunt mollit anim id est laborum lorem."),
        ("letter", "cover_letter.html", "Lorem Ipsum - Cover Letter",
         "Reprehenderit voluptate velit esse cillum fugiat nulla pariatur excepteur sint occaecat cupidatat."),
    ],
)  # fmt: skip
def test_the_default_templates_are_the_given_pages_byte_for_byte(kind, given, title, description):
    page = render_html(sample(kind), kind=kind, template=default_template(kind), title=title, description=description)
    assert page.decode() == (GIVEN / given).read_text()


def test_the_defaults_pass_every_check():
    assert check_template(default_template("sections"), "sections") == []
    assert check_template(default_template("letter"), "letter") == []


def test_headings_whatever_the_model_ranks_them_are_the_templates():
    doc = parts(
        "# Sam\n\nsam@x.example\n\n#### Experience\n\n###### Engineer, Himal, 2020 to 2024\n\n- Built", "sections"
    )
    assert doc["name"] == [{"s": "text", "v": "Sam"}]
    section = doc["sections"][0]
    assert section["heading"] == [{"s": "text", "v": "Experience"}]
    assert section["blocks"][0]["t"] == "article" and section["blocks"][0]["blocks"][0]["t"] == "ul"
    page = render_html(
        "# Sam\n\n### A\n\n#### B\n\n- x", template=default_template("sections"), title="T", description=""
    )
    assert "<h2>A</h2>" in page.decode() and "<h3>B</h3>" in page.decode()


def test_a_letter_keeps_its_lines_and_its_date():
    md = "# Sam Rai\n\nDenton\n\nOctober 27, 2026\n\nDear Hiring Manager,\n\nWhy.\n\nSincerely,\nSam Rai"
    page = render_html(md, kind="letter", template=default_template("letter"), title="T", description="").decode()
    assert "  <p>October 27, 2026</p>\n  <article>\n    <p>Dear Hiring Manager,</p>" in page
    assert "<p>Sincerely,<br>Sam Rai</p>" in page


def test_nothing_in_a_document_is_read_as_html():
    md = '# <script>alert(1)</script>\n\n<img src=x onerror=alert(1)> | [x](javascript:alert(1)) "quoted"'
    page = render_html(md, template=default_template("sections"), title='"><script>', description="<b>").decode()
    assert "<script>" not in page and "<img" not in page and "javascript:" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_the_profile_header_replaces_the_models():
    resume = with_letterhead("# Sam\n\nsam@x | 555\n\n## Professional Summary\n\nHi", "Sam Rai", "Denton", "sections")
    assert resume == "# Sam Rai\n\nDenton\n\n## Professional Summary\n\nHi\n"
    letter = with_letterhead("Sam\n\nOct 1\n\nDear Ms Lee,\n\nWhy.", "Sam Rai", "Denton", "letter", "October 27, 2026")
    assert letter == "# Sam Rai\n\nDenton\n\nOctober 27, 2026\n\nDear Ms Lee,\n\nWhy.\n"
    assert with_letterhead("Anything", "", "", "sections") == "Anything"


def _fonts(pdf: bytes) -> set[str]:
    reader = PdfReader(io.BytesIO(pdf))
    out = set()
    for page in reader.pages:
        for font in page["/Resources"]["/Font"].values():
            descriptor = font["/DescendantFonts"][0].get_object()["/FontDescriptor"]
            out.add(TTFont(io.BytesIO(descriptor["/FontFile2"].get_object().get_data()))["name"].getDebugName(4))
    return out


def test_the_pdf_is_the_page_printed_tagged_with_our_fonts_only():
    page = render_html(sample("sections"), template=default_template("sections"), title="Lorem Ipsum - Resume",
                       description="")  # fmt: skip
    pdf = render_pdf(page)
    reader = PdfReader(io.BytesIO(pdf))
    root = reader.trailer["/Root"]
    assert "/StructTreeRoot" in root and root["/MarkInfo"]["/Marked"] and root["/Lang"] == "en"
    assert reader.metadata["/Title"] == "Lorem Ipsum - Resume"
    assert root["/ViewerPreferences"]["/DisplayDocTitle"]
    assert float(reader.pages[0].mediabox.width) == 612  # US Letter, as the template's 8.5in page
    assert _fonts(pdf) == {"Arimo Regular", "Arimo Bold"}  # never the computer's own Arial


def test_nepali_is_printed_in_noto_and_paper_can_be_a4():
    md = "# सम राई\n\nकाठमाडौं\n\n## सारांश\n\nपाइथन र Python"
    page = render_html(md, template=default_template("sections"), title="सम राई - बायोडाटा", description="", lang="ne")
    pdf = render_pdf(page, paper="a4")
    assert "Noto Sans Devanagari Regular" in _fonts(pdf)
    assert round(float(PdfReader(io.BytesIO(pdf)).pages[0].mediabox.width)) == 595


def test_printing_fetches_nothing():
    template = default_template("sections").replace(
        "<main>", '<main>\n  <img alt="" src="https://tracker.example/pixel.png">'
    )
    pdf = render_pdf(render_html("# A", template=template, title="T", description=""))
    assert pdf.startswith(b"%PDF-")  # the image just isn't there; nothing was asked for
