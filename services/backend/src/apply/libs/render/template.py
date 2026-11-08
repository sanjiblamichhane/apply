"""
The templates documents are made in: an HTML page with placeholders, one laid out in sections (a resume, a
capability statement) and one for letters. Each person may upload their own; until they do, the defaults here
(templates/sections.html, templates/letter.html) are used.
A template is filled, never run: it has no logic, only these placeholders.

    {{lang}} {{title}} {{description}}   the page's language, title ("Sam Rai - Resume") and summary
    {{name}}                             the person's name
    {{contact}}                          the contact line: "Denton, TX | Phone: <a href="tel:…">…</a> | …"
    {{date}}                             a letter's date ("October 27, 2026")
    {{content}}                          the document itself, as the template's elements:
        sections: <section><h2>…</h2> <p>…</p> <ul><li>…</li></ul> <article><h3>…</h3> <ul>…</ul></article></section>…
        letter: <p>Dear …,</p> <p>…</p> <p>Sincerely,<br>Sam Rai</p>

{{content}} on a line of its own is indented as that line is. Every value is escaped; the only links are to
the web, an e-mail address or a phone number. tests/support/templates/ holds the default pages as given, and a
test fills the defaults from the samples (samples/) and gets them back, byte for byte.

The defaults' colours (text #000000, accent #1f3864, on #ffffff: 21:1 and 11.6:1) pass WCAG 2.2 AA; links stay
underlined on screen (never told apart by colour alone) and have a 3px focus outline. An uploaded template must
pass libs/render/checks.py before it's kept.
"""

import re
from html import escape
from importlib.resources import files
from typing import Any, Literal

Kind = Literal["sections", "letter"]
KINDS: tuple[Kind, ...] = ("sections", "letter")
PLACEHOLDERS = frozenset({"lang", "title", "description", "name", "contact", "date", "content"})
PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
MAX_TEMPLATE_BYTES = 256 * 1024


def default_template(kind: Kind) -> str:
    return files("apply.libs.render").joinpath(f"templates/{kind}.html").read_text(encoding="utf-8")


def sample(kind: Kind) -> str:
    """Made-up words in every part a document has: what a template is checked and previewed with."""
    return files("apply.libs.render").joinpath(f"samples/{kind}.md").read_text(encoding="utf-8")


def inline(xs: list[dict[str, str]]) -> str:
    out = []
    for s in xs:
        v = escape(s["v"], quote=False)
        if s["s"] == "strong":
            out.append(f"<strong>{v}</strong>")
        elif s["s"] == "emph":
            out.append(f"<em>{v}</em>")
        elif s["s"] == "link":
            out.append(f'<a href="{escape(s["href"])}">{v}</a>')
        elif s["s"] == "br":
            out.append("<br>")
        else:
            out.append(v)
    return "".join(out).strip()


def _blocks(bs: list[dict[str, Any]], pad: str = "") -> list[str]:
    lines = []
    for b in bs:
        if b["t"] == "p":
            lines.append(f"{pad}<p>{inline(b['spans'])}</p>")
        elif b["t"] in ("ul", "ol"):
            lines.append(f"{pad}<{b['t']}>")
            lines += [f"{pad}  <li>{inline(item)}</li>" for item in b["items"]]
            lines.append(f"{pad}</{b['t']}>")
        elif b["t"] == "article":
            lines.append(f"{pad}<article>")
            lines.append(f"{pad}  <h3>{inline(b['heading'])}</h3>")
            lines += _blocks(b["blocks"], pad + "  ")
            lines.append(f"{pad}</article>")
    return lines


def content(doc: dict[str, Any]) -> list[str]:
    """The document's own elements, as lines (indented by where {{content}} stands)."""
    if doc["kind"] == "letter":
        return _blocks(doc["body"])
    lines = []
    for section in doc["sections"]:
        lines.append("<section>")
        if section["heading"]:
            lines.append(f"  <h2>{inline(section['heading'])}</h2>")
        lines += _blocks(section["blocks"], "  ")
        lines.append("</section>")
    return lines


def fill(template: str, doc: dict[str, Any], *, title: str, description: str, lang: str = "en") -> str:
    contact = " | ".join(inline(c) for c in doc["contact"] if c)
    values = {
        "lang": escape(lang),
        "title": escape(title),
        "description": escape(description),
        "name": inline(doc["name"]) or escape(title, quote=False),
        "contact": contact,
        "date": inline(doc.get("date") or []),
    }
    lines = content(doc)

    def place(m: re.Match[str]) -> str:
        return values.get(m.group(1), "")

    out = []
    for line in template.split("\n"):
        alone = re.fullmatch(r"(\s*)\{\{\s*content\s*\}\}\s*", line)
        if alone:
            out += [alone.group(1) + x for x in lines]
        else:
            out.append(PLACEHOLDER.sub(lambda m: "\n".join(lines) if m.group(1) == "content" else place(m), line))
    return "\n".join(out)
