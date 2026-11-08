"""
Documents as files, in the person's own templates (template.py; a default for each until they upload theirs):
the document's page (HTML), and that same page printed to a tagged PDF/UA-1 by the PDF renderer, so the PDF is the
page, whatever the template's CSS says. Markdown (the subset a model writes: headings, paragraphs, lists, bold,
italics, links) is parsed into the template's parts first, and every value is escaped: nothing in a document
is ever read as HTML. Printing fetches nothing; Arial and Helvetica are Arimo (metric-compatible), with Noto
Sans Devanagari for Nepali (OFL, embedded).

    page = render_html(markdown, kind="sections", template=default_template("sections"), title=…, description=…)
    pdf = render_pdf(page)
    problems = check_template(uploaded_html, "letter")   # [] when it may be kept
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Literal

from .checks import Problem, accessibility, safety
from .template import KINDS, MAX_TEMPLATE_BYTES, Kind, default_template, fill, sample

HERE = Path(__file__).parent
FONTS = HERE / "fonts"

__all__ = [
    "KINDS",
    "MAX_TEMPLATE_BYTES",
    "Kind",
    "Problem",
    "blocks",
    "check_template",
    "default_template",
    "parts",
    "render_html",
    "render_pdf",
    "sample",
    "spans",
    "with_letterhead",
]

_INLINE = re.compile(
    r"\*\*(?P<strong>.+?)\*\*|__(?P<strong2>.+?)__|(?<![\w*])\*(?P<emph>[^*\n]+?)\*(?![\w*])"
    r"|(?<![\w_])_(?P<emph2>[^_\n]+?)_(?![\w_])|`(?P<code>[^`\n]+)`|\[(?P<ltext>[^\]\n]+)\]\((?P<href>(?:[^()\s]|\([^()\s]*\))+)\)"
)
_SAFE_LINK = re.compile(r"^(https?://\S+|mailto:[^\s@]+@\S+|tel:\+?[0-9]{3,20})$", re.IGNORECASE)
_LABELLED = re.compile(r"^\*\*[^*\n]+?:\*\*")  # "**Tools:** …": a line of its own, as in the template's skills


def spans(text: str) -> list[dict[str, str]]:
    """Inline markdown as spans; anything not understood stays as plain text. A line break is {"s": "br"}."""
    out: list[dict[str, str]] = []
    for n, line in enumerate(text.split("\n")):
        if n:
            out.append({"s": "br", "v": "\n"})
        pos = 0
        for m in _INLINE.finditer(line):
            if m.start() > pos:
                out.append({"s": "text", "v": line[pos : m.start()]})
            if m.group("strong") or m.group("strong2"):
                out.append({"s": "strong", "v": m.group("strong") or m.group("strong2")})
            elif m.group("emph") or m.group("emph2"):
                out.append({"s": "emph", "v": m.group("emph") or m.group("emph2")})
            elif m.group("code"):
                out.append({"s": "text", "v": m.group("code")})  # a resume has no code: its words
            elif _SAFE_LINK.match(m.group("href")):
                out.append({"s": "link", "v": m.group("ltext"), "href": m.group("href")})
            else:  # a link to somewhere odd (javascript:, a file): just its words
                out.append({"s": "text", "v": m.group("ltext")})
            pos = m.end()
        if pos < len(line):
            out.append({"s": "text", "v": line[pos:]})
    return [s for s in out if s["v"]]


def blocks(markdown: str, *, keep_lines: bool = False) -> list[dict[str, Any]]:
    """
    Block markdown as a list of headings, paragraphs and lists. A paragraph's lines are joined into one, or,
    with ``keep_lines`` (a letter's "Sincerely,\\nSam Rai"), kept as lines.
    """
    out: list[dict[str, Any]] = []
    para: list[str] = []
    items: list[str] = []
    kind = ""

    def flush() -> None:
        nonlocal para, items, kind
        if para:
            out.append({"t": "p", "spans": spans(("\n" if keep_lines else " ").join(para))})
        if items:
            out.append({"t": kind, "items": [spans(i) for i in items]})
        para, items, kind = [], [], ""

    for raw in markdown.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        bullet = re.match(r"^[-*+•]\s+(.*)$", stripped)
        number = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if not stripped or re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flush()  # a rule only ends what came before: the template draws its own lines
        elif heading:
            flush()
            out.append({"t": "h", "level": len(heading.group(1)), "spans": spans(heading.group(2).strip())})
        elif bullet or number:
            this = "ul" if bullet else "ol"
            if para or (items and kind != this):
                flush()
            kind = this
            items.append((bullet or number).group(1))  # type: ignore[union-attr]
        elif items and raw.startswith(("  ", "\t")):
            items[-1] += " " + stripped  # a list item's next line
        else:
            if items or (para and _LABELLED.match(stripped)):
                flush()
            para.append(stripped)
    flush()
    return out


def _words(xs: list[dict[str, str]]) -> str:
    return "".join(s["v"] for s in xs if s["s"] != "br").strip()


def parts(markdown: str, kind: Kind = "sections") -> dict[str, Any]:
    """
    A document as the template's parts: the header (the name, the contact line), then

    - a resume: sections, each with its heading (h2), its paragraphs and lists, and its entries (an h3 and what
      follows it: a job, a degree with details);
    - a letter: the date, then the letter itself.

    However the markdown ranks its headings, the name is the only h1, sections are h2 and entries h3: the
    outline never skips a level (WCAG 1.3.1, PDF/UA-1).
    """
    out: list[dict[str, Any]] = blocks(markdown, keep_lines=kind == "letter")
    name: list[dict[str, str]] = []
    contact: list[list[dict[str, str]]] = []
    if out and out[0]["t"] == "h":
        name = out.pop(0)["spans"]
        while out and out[0]["t"] == "p" and not _opens_letter(out[0]) and (kind == "sections" or not contact):
            contact.append(out.pop(0)["spans"])
            if kind == "letter":
                break
    doc: dict[str, Any] = {"kind": kind, "name": name, "contact": contact}

    if kind == "letter":
        date: list[dict[str, str]] = []
        if out and out[0]["t"] == "p" and not _opens_letter(out[0]) and len(_words(out[0]["spans"])) <= 40:
            date = out.pop(0)["spans"]
        for b in out:
            if b["t"] == "h":  # a letter has no headings: its words, as a paragraph
                b.update(t="p", spans=[{"s": "strong", "v": _words(b["spans"])}])
        return {**doc, "date": date, "body": out}

    levels = sorted({b["level"] for b in out if b["t"] == "h"})
    sections: list[dict[str, Any]] = []
    entry: dict[str, Any] | None = None
    for b in out:
        if b["t"] == "h" and b["level"] == levels[0]:
            sections.append({"heading": b["spans"], "blocks": []})
            entry = None
            continue
        if not sections:
            sections.append({"heading": [], "blocks": []})  # words before any heading: a section of their own
        if b["t"] == "h":
            entry = {"t": "article", "heading": b["spans"], "blocks": []}
            sections[-1]["blocks"].append(entry)
        elif entry is not None:
            entry["blocks"].append(b)
        else:
            sections[-1]["blocks"].append(b)
    return {**doc, "sections": sections}


def _opens_letter(b: dict[str, Any]) -> bool:
    return b["t"] == "p" and bool(re.match(r"^(dear|to whom|hello|hi)\b", _words(b["spans"]), re.IGNORECASE))


_SALUTATION = re.compile(r"^(dear|to whom|hello|hi)\b", re.IGNORECASE)
_CONTACTISH = re.compile(r"@|\||\+?\d[\d\s().-]{6,}|https?://|linkedin", re.IGNORECASE)


def with_letterhead(markdown: str, name: str, contact: str, kind: Kind, date: str = "") -> str:
    """
    The document with the template's header from the profile in place of whatever header the model wrote (the
    name as the one "# " heading, the contact line under it) and, in a letter, the date before the salutation.
    A document with no name to put stays as it is.
    """
    if not name:
        return markdown
    paras = [p.strip() for p in re.split(r"\n\s*\n", markdown.replace("\r\n", "\n").strip()) if p.strip()]
    if kind == "letter":
        opening = next((i for i, p in enumerate(paras[:8]) if _SALUTATION.match(p)), None)
        if opening is not None:
            paras = paras[opening:]
        else:
            while paras and (paras[0].startswith("# ") or _CONTACTISH.search(paras[0])):
                paras.pop(0)
    elif paras and paras[0].startswith("# "):
        paras.pop(0)
        while paras and not paras[0].startswith("#"):
            paras.pop(0)  # the model's contact lines: the profile's are put instead
    else:
        while paras and not paras[0].startswith("#") and _CONTACTISH.search(paras[0]):
            paras.pop(0)
    head = [f"# {name}"] + ([contact] if contact else []) + ([date] if kind == "letter" and date else [])
    return "\n\n".join(head + paras) + "\n"


def render_html(
    markdown: str, *, kind: Kind = "sections", template: str, title: str, description: str, lang: str = "en"
) -> bytes:
    """The template filled in with the document."""
    return fill(template, parts(markdown, kind), title=title, description=description, lang=lang).encode()


def check_template(template: str, kind: Kind) -> list[Problem]:
    """What stops a template being kept: anything unsafe in it, and, filled with a sample, WCAG 2.2 AA."""
    problems = safety(template)
    if any(p.code == "placeholder" for p in problems):
        return problems  # it can't be filled to check the rest
    page = fill(template, parts(sample(kind), kind), title="Lorem Ipsum - Sample", description="A sample.")
    return problems + accessibility(page)


# Printing sees only apply's own fonts, the same on every machine (a laptop's fonts never leak into a PDF):
# Arimo, metric-compatible with Arial and Helvetica, for every family a template names, and Noto Sans
# Devanagari for Nepali. Fontconfig reads this before the PDF renderer first loads.
_FONTCONF = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>{fonts}</dir>
  <cachedir>{cache}</cachedir>
  <match target="pattern">
    <edit name="family" mode="prepend" binding="strong"><string>Arimo</string></edit>
    <edit name="family" mode="append" binding="strong"><string>Noto Sans Devanagari</string></edit>
  </match>
</fontconfig>
"""


_fonts_set = False


def _use_our_fonts() -> None:
    global _fonts_set
    if _fonts_set:
        return
    folder = Path(tempfile.mkdtemp(prefix="apply-fonts-"))
    conf = folder / "fonts.conf"
    conf.write_text(_FONTCONF.format(fonts=FONTS, cache=folder / "cache"))
    os.environ["FONTCONFIG_FILE"] = str(conf)
    _fonts_set = True


def render_pdf(page: bytes | str, *, paper: Literal["a4", "us-letter"] = "us-letter") -> bytes:
    """
    The page, printed as its print styles say, to a tagged PDF/UA-1 (its language, title and headings kept). A
    template without its own @page is printed on ``paper`` with the default templates' 0.6in margins.
    """
    _use_our_fonts()
    from weasyprint import CSS, HTML
    from weasyprint.urls import URLFetcher

    # Printing fetches nothing but what's inline (data:): a template can't make the worker reach anywhere.
    nothing = URLFetcher(allowed_protocols={"data"}, allow_redirects=False)
    size = "letter" if paper == "us-letter" else "A4"
    html = HTML(string=page.decode() if isinstance(page, bytes) else page, url_fetcher=nothing)
    return html.write_pdf(stylesheets=[CSS(string=f"@page {{ size: {size}; margin: 0.6in; }}")], pdf_variant="pdf/ua-1")
