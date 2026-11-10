"""
A document as a Word file (.docx), to edit in a word processor. Made from the same parts as the page and the PDF
(``parts``), in Word's own styles rather than the HTML template: the name is Heading 1, sections Heading 2,
entries Heading 3, lists Word's lists, links real links. So the outline is the PDF's, a screen reader can move by
headings, and the person can restyle it in Word. Every value is text: nothing in a document is read as markup.
"""

import io
import re
from typing import Any, Literal
from xml.sax.saxutils import escape

from docx import Document as new_document
from docx.enum.text import WD_COLOR_INDEX
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor
from docx.text.paragraph import Paragraph

from .template import Kind

PAPER = {"us-letter": (Inches(8.5), Inches(11)), "a4": (Inches(8.27), Inches(11.69))}
TEXT = RGBColor(0x1A, 0x1A, 0x1A)  # near black on white: 17.4:1
LINK = RGBColor(0x0B, 0x57, 0xD0)  # underlined as well as coloured: 6.39:1 on white
# Characters XML 1.0 can't hold: a model's stray control character must not make a file Word refuses to open.
_NOT_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def render_docx(
    parts_: dict[str, Any],
    *,
    title: str,
    description: str,
    lang: str = "en",
    paper: Literal["a4", "us-letter"] = "us-letter",
) -> bytes:
    """The document's parts (``parts(markdown, kind)``) as a .docx."""
    doc = new_document()
    _setup(doc, title=title, description=description, lang=lang, paper=paper)
    kind: Kind = parts_["kind"]
    if parts_.get("name"):
        _runs(doc.add_heading(level=1), parts_["name"])
    for line in parts_.get("contact") or []:
        _runs(doc.add_paragraph(), line)
    if kind == "letter":
        if parts_.get("date"):
            _runs(doc.add_paragraph(), parts_["date"])
        for block in parts_.get("body") or []:
            _block(doc, block)
    else:
        for section in parts_.get("sections") or []:
            if section["heading"]:
                _runs(doc.add_heading(level=2), section["heading"])
            for block in section["blocks"]:
                if block["t"] == "article":
                    _runs(doc.add_heading(level=3), block["heading"])
                    for inner in block["blocks"]:
                        _block(doc, inner)
                else:
                    _block(doc, block)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _setup(doc: Any, *, title: str, description: str, lang: str, paper: str) -> None:
    props = doc.core_properties
    props.title, props.subject, props.language = _clean(title), _clean(description), lang
    props.author = props.last_modified_by = ""
    props.comments = props.keywords = ""
    section = doc.sections[0]
    section.page_width, section.page_height = PAPER[paper]
    section.left_margin = section.right_margin = section.top_margin = section.bottom_margin = Inches(0.8)
    # Arial everywhere: on every computer, and the PDF's Arimo is drawn to its measurements.
    for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "List Bullet", "List Number"):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.color.rgb = TEXT
        props_ = style.element.get_or_add_rPr()
        # Every script's font is Arial (not the theme's), and the text is in the document's language.
        _only(props_, "rFonts", {script: "Arial" for script in ("ascii", "hAnsi", "cs", "eastAsia")})
        _only(props_, "lang", {"val": lang})
    doc.styles["Normal"].font.size = Pt(10.5)
    doc.styles["Normal"].paragraph_format.space_after = Pt(4)
    for name, size in (("Heading 1", 20), ("Heading 2", 13), ("Heading 3", 11)):
        style = doc.styles[name]
        style.font.size = Pt(size)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(10 if name != "Heading 1" else 0)
        style.paragraph_format.space_after = Pt(3)


def _block(doc: Any, block: dict[str, Any]) -> None:
    if block["t"] == "p":
        _runs(doc.add_paragraph(), block["spans"])
    elif block["t"] in ("ul", "ol"):
        style = "List Bullet" if block["t"] == "ul" else "List Number"
        for item in block["items"]:
            _runs(doc.add_paragraph(style=style), item)
    elif block["t"] == "h":
        _runs(doc.add_heading(level=3), block["spans"])


def _runs(paragraph: Paragraph, spans: list[dict[str, str]]) -> None:
    for span in spans:
        if span["s"] == "br":
            paragraph.add_run().add_break()
        elif span["s"] == "link":
            _link(paragraph, _clean(span["v"]), span["href"])
        else:
            run = paragraph.add_run(_clean(span["v"]))
            run.bold = span["s"] == "strong" or None
            run.italic = span["s"] == "emph" or None
            if "[CONFIRM:" in span["v"]:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW  # left for the person: easy to find in Word


def _link(paragraph: Paragraph, text: str, href: str) -> None:
    """A real hyperlink (python-docx has none of its own): underlined, so it isn't told by colour alone."""
    target = paragraph.part.relate_to(href, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    paragraph._p.append(
        parse_xml(
            f'<w:hyperlink {nsdecls("w", "r")} r:id="{target}"><w:r><w:rPr><w:color w:val="{LINK}"/>'
            f'<w:u w:val="single"/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:hyperlink>'
        )
    )


def _only(parent: Any, tag: str, values: dict[str, str]) -> None:
    """``parent``'s one ``w:tag`` child, made anew with just these ``w:`` attributes."""
    for old in parent.findall(qn(f"w:{tag}")):
        parent.remove(old)
    parent.append(parse_xml(f"<w:{tag} {nsdecls('w')} " + " ".join(f'w:{k}="{v}"' for k, v in values.items()) + "/>"))


def _clean(text: str) -> str:
    return _NOT_XML.sub("", text)
