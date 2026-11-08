"""
What an uploaded template must pass before it's kept, each problem named with where it is and, for
accessibility, the WCAG 2.2 success criterion:

- **Safe**: a page to read and print, nothing more. No scripts, frames, forms or embedded objects; no event
  handlers; no addresses but the web, e-mail and phone in links; nothing fetched from elsewhere (an image is
  inline, as data:); only the placeholders template.py fills, with {{content}} once.
- **Accessible** (WCAG 2.2 AA), checked on the template filled with a sample document, so the person's own
  documents are checked the same way:
  - The page: its language (3.1.1) and title (2.4.2). Zoom not turned off (1.4.4). One <main>, and nothing
    outside landmarks (1.3.1).
  - Headings: one h1, no level skipped, none empty (1.3.1, 2.4.6).
  - Content: images described (1.1.1), links named (2.4.4, 4.1.2), no positive tabindex (2.4.3), nothing hidden
    from assistive technology that's shown.
  - The CSS, rule by rule: text against its background at 4.5:1 (1.4.3), custom properties and transparency
    resolved; links told apart from text other than by colour (1.4.1); focus never hidden, and its outline at
    3:1 (2.4.7, 1.4.11); no fixed width that stops the page reflowing at 320px (1.4.10); no fixed height that
    cuts off spaced-out text (1.4.12).

Automated checks can't see everything (whether a heading's words describe its section, say); the tests also
run axe-core in a browser on the default templates and on a template changed in every way allowed.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

import tinycss2
import tinycss2.color3

from .template import MAX_TEMPLATE_BYTES, PLACEHOLDER, PLACEHOLDERS


@dataclass(frozen=True)
class Problem:
    code: str  # unsafe, placeholder, lang, title, zoom, landmark, heading, image, link, focus_order, hidden,
    # contrast, link_colour, focus, reflow, spacing
    message: str  # in plain English, saying where
    wcag: str = ""  # the success criterion, for accessibility problems ("1.4.3")


# ── a light tree of the page ─────────────────────────────────────────────────

VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"})
FORBIDDEN = frozenset(
    {
        "script", "noscript", "iframe", "frame", "frameset", "object", "embed", "applet", "form", "input",
        "button", "select", "textarea", "link", "base", "svg", "math", "video", "audio", "canvas", "template",
        "portal", "dialog",
    }
)  # fmt: skip
LANDMARKS = frozenset({"header", "main", "footer", "nav", "aside"})
URL_ATTRS = frozenset({"href", "src", "action", "formaction", "poster", "background", "cite", "srcset", "xlink:href"})


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    parent: "Node | None" = None
    children: list["Node | str"] = field(default_factory=list)

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.walk()

    def ancestors(self):
        p = self.parent
        while p is not None:
            yield p
            p = p.parent


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self.at = self.root
        self.doctype = ""

    def handle_decl(self, decl: str) -> None:
        self.doctype = decl

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {k.lower(): v or "" for k, v in attrs}, self.at)
        self.at.children.append(node)
        if tag not in VOID:
            self.at = node

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.at.children.append(Node(tag, {k.lower(): v or "" for k, v in attrs}, self.at))

    def handle_endtag(self, tag: str) -> None:
        for node in [self.at, *self.at.ancestors()]:
            if node.tag == tag:
                self.at = node.parent or self.root
                return

    def handle_data(self, data: str) -> None:
        self.at.children.append(data)


def parse(html: str) -> Node:
    tree = _Tree()
    tree.feed(html)
    tree.close()
    return tree.root


# ── safe ─────────────────────────────────────────────────────────────────────

_SAFE_HREF = re.compile(r"^(https?://|mailto:|tel:|#|\{\{)", re.IGNORECASE)
_DATA_IMAGE = re.compile(r"^data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+$", re.IGNORECASE)
_CSS_UNSAFE = re.compile(r"@import|expression\s*\(|behavior\s*:|-moz-binding|javascript:", re.IGNORECASE)
_CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]*)", re.IGNORECASE)


def safety(template: str) -> list[Problem]:
    problems: list[Problem] = []
    if len(template.encode()) > MAX_TEMPLATE_BYTES:
        problems.append(Problem("unsafe", f"The template is over {MAX_TEMPLATE_BYTES // 1024} KB."))
    used = [m.group(1) for m in PLACEHOLDER.finditer(template)]
    for name in sorted(set(used) - PLACEHOLDERS):
        problems.append(Problem("placeholder", f"{{{{{name}}}}} isn't a placeholder apply fills."))
    if used.count("content") != 1:
        problems.append(
            Problem("placeholder", "{{content}} must be in the template once: it's where the document goes.")
        )
    for needed in ("title", "name"):
        if needed not in used:
            problems.append(Problem("placeholder", f"{{{{{needed}}}}} is missing."))
    for node in parse(template).walk():
        if node.tag in FORBIDDEN:
            problems.append(Problem("unsafe", f"<{node.tag}> isn't allowed: a template is a page to read and print."))
        if node.tag == "meta" and node.attrs.get("http-equiv"):
            problems.append(Problem("unsafe", "<meta http-equiv> isn't allowed."))
        for name, value in node.attrs.items():
            if name.startswith("on"):
                problems.append(Problem("unsafe", f"<{node.tag} {name}>: event handlers aren't allowed."))
            elif name in URL_ATTRS:
                v = value.strip()
                if node.tag == "img" and name == "src" and _DATA_IMAGE.match(v):
                    continue
                if name != "href" or not _SAFE_HREF.match(v):
                    problems.append(
                        Problem(
                            "unsafe",
                            f'<{node.tag} {name}="{v[:60]}">: only links to the web, an e-mail '
                            "address or a phone, and images inline (data:image/…), are allowed.",
                        )
                    )
            elif name == "style":
                problems += _css_safety(value, f"<{node.tag} style>")
        if node.tag == "style":
            problems += _css_safety(node.text(), "<style>")
    return problems


def _css_safety(css: str, where: str) -> list[Problem]:
    problems = []
    if _CSS_UNSAFE.search(css):
        problems.append(Problem("unsafe", f"{where}: @import, expression() and bindings aren't allowed."))
    for url in _CSS_URL.findall(css):
        if not _DATA_IMAGE.match(url.strip()) and not url.strip().lower().startswith("data:font/"):
            problems.append(
                Problem("unsafe", f"{where}: url({url[:60]}) would fetch from elsewhere; inline it as data:.")
            )
    return problems


# ── accessible ───────────────────────────────────────────────────────────────


def accessibility(page: str) -> list[Problem]:
    """The filled page (template.fill with a sample) against WCAG 2.2 AA."""
    root = parse(page)
    nodes = list(root.walk())
    problems: list[Problem] = []

    def first(tag: str) -> Node | None:
        return next((n for n in nodes if n.tag == tag), None)

    html = first("html")
    if html is None or not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", html.attrs.get("lang", "").strip()):
        problems.append(Problem("lang", '<html lang="…"> must say the page\'s language.', "3.1.1"))
    title = first("title")
    if title is None or not title.text().strip():
        problems.append(Problem("title", "The page needs a <title> ({{title}}).", "2.4.2"))
    for meta in (n for n in nodes if n.tag == "meta" and n.attrs.get("name", "").lower() == "viewport"):
        content = meta.attrs.get("content", "").lower().replace(" ", "")
        scale = re.search(r"maximum-scale=([\d.]+)", content)
        if re.search(r"user-scalable=(no|0)", content) or (scale and float(scale.group(1)) < 2):
            problems.append(Problem("zoom", "The viewport turns zoom off (user-scalable, maximum-scale).", "1.4.4"))

    mains = [n for n in nodes if n.tag == "main" or n.attrs.get("role") == "main"]
    if len(mains) != 1:
        problems.append(Problem("landmark", "The page needs one <main>, around the document.", "1.3.1"))
    body = first("body")
    if body is not None:
        for c in body.children:
            outside = (isinstance(c, str) and c.strip()) or (
                isinstance(c, Node)
                and c.tag not in LANDMARKS | FORBIDDEN | {"style"}
                and c.attrs.get("role")
                not in ("main", "banner", "contentinfo", "navigation", "complementary", "region")
                and c.text().strip()
            )
            if outside:
                where = f"<{c.tag}>" if isinstance(c, Node) else f'"{c.strip()[:40]}"'
                problems.append(Problem("landmark", f"{where} is outside <main> (or <header>, <footer>).", "1.3.1"))

    headings = [n for n in nodes if re.fullmatch(r"h[1-6]", n.tag)]
    if sum(1 for h in headings if h.tag == "h1") != 1:
        problems.append(Problem("heading", "The page needs one <h1> ({{name}}).", "1.3.1"))
    previous = 0
    for h in headings:
        level = int(h.tag[1])
        if not h.text().strip():
            problems.append(Problem("heading", f"An empty <{h.tag}>.", "2.4.6"))
        if previous and level > previous + 1:
            problems.append(Problem("heading", f"<{h.tag}> comes after <h{previous}>: a level is skipped.", "1.3.1"))
        previous = level

    for n in nodes:
        if n.tag == "img" and "alt" not in n.attrs:
            problems.append(Problem("image", 'An <img> without alt (alt="" if it\'s only decoration).', "1.1.1"))
        if n.tag == "a" and n.attrs.get("href") and not (n.text().strip() or n.attrs.get("aria-label", "").strip()):
            problems.append(Problem("link", f"A link to {n.attrs['href'][:60]} has no words.", "2.4.4"))
        tabindex = n.attrs.get("tabindex", "").strip()
        if tabindex.lstrip("-").isdigit() and int(tabindex) > 0:
            problems.append(
                Problem("focus_order", f"<{n.tag} tabindex={tabindex}> changes the reading order.", "2.4.3")
            )
        if n.tag in ("body", "main", "html") and n.attrs.get("aria-hidden", "").lower() == "true":
            problems.append(Problem("hidden", f"<{n.tag} aria-hidden> hides the page from screen readers.", "1.3.1"))

    css = "\n".join(n.text() for n in nodes if n.tag == "style")
    inline_styles = [(n.tag, n.attrs["style"]) for n in nodes if n.attrs.get("style")]
    problems += _css(css, inline_styles)
    return problems


# ── the CSS ──────────────────────────────────────────────────────────────────

RGBA = tuple[float, float, float, float]
WHITE: RGBA = (1.0, 1.0, 1.0, 1.0)
BLACK: RGBA = (0.0, 0.0, 0.0, 1.0)
_VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\))?[^()]*))?\)")
_ABSOLUTE = {"px": 1.0, "pt": 4 / 3, "pc": 16.0, "in": 96.0, "cm": 96 / 2.54, "mm": 96 / 25.4, "q": 96 / 101.6}
TEXT_BOXES = re.compile(r"^(html|body|main|header|footer|section|article|p|ul|ol|li|h[1-6]|div|span|a|strong|em)$")


@dataclass
class Rule:
    selector: str
    decls: dict[str, str]
    print_only: bool


def _rules(css: str, inline_styles: list[tuple[str, str]]) -> list[Rule]:
    out: list[Rule] = []

    def walk(items: list[Any], print_only: bool) -> None:
        for item in items:
            if item.type == "qualified-rule":
                decls = {
                    d.lower_name: tinycss2.serialize(d.value).strip() + (" !important" if d.important else "")
                    for d in tinycss2.parse_blocks_contents(item.content, skip_whitespace=True, skip_comments=True)
                    if d.type == "declaration"
                }
                out.append(Rule(tinycss2.serialize(item.prelude).strip(), decls, print_only))
            elif item.type == "at-rule" and item.lower_at_keyword in ("media", "supports", "layer") and item.content:
                prelude = tinycss2.serialize(item.prelude).lower()
                printing = item.lower_at_keyword == "media" and "print" in prelude and "screen" not in prelude
                walk(
                    tinycss2.parse_stylesheet(item.content, skip_whitespace=True, skip_comments=True),
                    print_only or printing,
                )

    walk(tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True), False)
    for tag, style in inline_styles:
        decls = {
            d.lower_name: tinycss2.serialize(d.value).strip()
            for d in tinycss2.parse_declaration_list(style, skip_whitespace=True, skip_comments=True)
            if d.type == "declaration"
        }
        out.append(Rule(f"<{tag} style>", decls, False))
    return out


def _resolve(value: str, props: dict[str, str], depth: int = 0) -> str:
    if depth > 10:
        return value
    return _VAR.sub(lambda m: _resolve(props.get(m.group(1), m.group(2) or ""), props, depth + 1), value)


def _colour(value: str) -> RGBA | None:
    """The colour in a value (a background's colour among its other parts), or None if there isn't one."""
    for token in tinycss2.parse_component_value_list(value):
        if token.type in ("whitespace", "comment"):
            continue
        parsed = tinycss2.color3.parse_color(token)
        if parsed is not None and parsed != "currentColor":
            return tuple(parsed)  # type: ignore[return-value]
    return None


def _over(fg: RGBA, bg: RGBA) -> RGBA:
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1.0)


def _luminance(c: RGBA) -> float:
    def ch(x: float) -> float:
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(a: RGBA, b: RGBA) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _hex(c: RGBA) -> str:
    return "#" + "".join(f"{round(x * 255):02x}" for x in c[:3])


def _selects(selector: str, *tags: str) -> bool:
    """Whether a selector's last part is one of these elements (or everything)."""
    for part in selector.split(","):
        last = re.split(r"[\s>+~]+", part.strip())[-1]
        name = re.match(r"^[a-zA-Z0-9*]+", last)
        if name and (name.group(0).lower() in tags or name.group(0) == "*"):
            return True
        if last.startswith(":root") and "html" in tags:
            return True
    return False


def _px(value: str) -> float | None:
    m = re.match(r"^\s*(-?[\d.]+)\s*([a-z]+)\s*$", value.lower())
    if m and m.group(2) in _ABSOLUTE:
        return float(m.group(1)) * _ABSOLUTE[m.group(2)]
    return None


def _css(css: str, inline_styles: list[tuple[str, str]]) -> list[Problem]:
    rules = _rules(css, inline_styles)
    problems: list[Problem] = []
    props: dict[str, str] = {}
    for r in rules:
        if _selects(r.selector, "html") or r.selector.startswith(":root"):
            props.update({k: v for k, v in r.decls.items() if k.startswith("--")})

    def colour(rule: Rule, *names: str) -> RGBA | None | str:
        for name in names:
            if name in rule.decls:
                value = _resolve(rule.decls[name].replace("!important", ""), props)
                if re.search(r"url\(|gradient\(", value, re.IGNORECASE):
                    return "image"
                found = _colour(value)
                if found is not None:
                    return found
        return None

    for printing in (False, True):
        media = "printed" if printing else "on screen"
        # The cascade, as far as it matters here: a later rule for the same selector wins, property by property.
        merged: dict[str, Rule] = {}
        for r in rules:
            if r.print_only == printing or not r.print_only:
                merged.setdefault(r.selector, Rule(r.selector, {}, printing)).decls.update(r.decls)
        active = list(merged.values())
        page_bg: RGBA = WHITE
        text: RGBA = BLACK
        for r in active:
            if _selects(r.selector, "html", "body"):
                bg = colour(r, "background-color", "background")
                if bg == "image":
                    problems.append(
                        Problem(
                            "contrast",
                            f"{r.selector}: a background image or gradient behind the "
                            "text can't be checked for contrast; use a colour.",
                            "1.4.3",
                        )
                    )
                elif bg is not None:
                    page_bg = _over(bg, WHITE)  # type: ignore[arg-type]
                fg = colour(r, "color")
                if isinstance(fg, tuple):
                    text = fg
        if printing:
            page_bg = WHITE  # paper

        link: RGBA = text
        for r in active:
            fg, bg = colour(r, "color"), colour(r, "background-color", "background")
            if bg == "image":
                if not _selects(r.selector, "html", "body"):
                    problems.append(
                        Problem(
                            "contrast",
                            f"{r.selector}: a background image or gradient behind "
                            "text can't be checked for contrast; use a colour.",
                            "1.4.3",
                        )
                    )
                continue
            behind = _over(bg, page_bg) if isinstance(bg, tuple) else page_bg  # type: ignore[arg-type]
            front = fg if isinstance(fg, tuple) else (text if isinstance(bg, tuple) else None)
            if front is not None:
                opacity = _resolve(r.decls.get("opacity", "1"), props).replace("!important", "").strip()
                try:
                    alpha = float(opacity[:-1]) / 100 if opacity.endswith("%") else float(opacity)
                except ValueError:
                    alpha = 1.0
                shown = _over((front[0], front[1], front[2], front[3] * min(alpha, 1.0)), behind)
                ratio = contrast(shown, behind)
                if ratio < 4.5:
                    problems.append(
                        Problem(
                            "contrast",
                            f"{r.selector} ({media}): text {_hex(shown)} on {_hex(behind)} is {ratio:.2f}:1; "
                            "it needs 4.5:1.",
                            "1.4.3",
                        )
                    )
            if _selects(r.selector, "a") and isinstance(fg, tuple) and not printing:
                link = fg

            if not printing:
                outline = r.decls.get("outline", "") + " " + r.decls.get("outline-style", "")
                hides = re.search(r"(^|\s)(none|0)(\s|$|!)", outline.strip()) and not (
                    "box-shadow" in r.decls or "border" in r.decls
                )
                if hides and (":focus" in r.selector or _selects(r.selector, "a", "*")):
                    problems.append(
                        Problem("focus", f"{r.selector}: outline none hides where the keyboard is.", "2.4.7")
                    )
                if ":focus" in r.selector:
                    ring = colour(r, "outline-color", "outline")
                    if isinstance(ring, tuple) and contrast(_over(ring, page_bg), page_bg) < 3:
                        problems.append(
                            Problem(
                                "focus",
                                f"{r.selector}: the focus outline is "
                                f"{contrast(_over(ring, page_bg), page_bg):.2f}:1; it needs 3:1.",
                                "1.4.11",
                            )
                        )
                for name in ("width", "min-width"):
                    px = _px(_resolve(r.decls.get(name, ""), props).replace("!important", ""))
                    if (
                        px is not None
                        and px > 320
                        and _selects(
                            r.selector, "html", "body", "main", "header", "section", "article", "p", "ul", "div"
                        )
                    ):
                        problems.append(
                            Problem(
                                "reflow",
                                f"{r.selector}: {name} {r.decls[name]} makes a phone scroll sideways; use max-width.",
                                "1.4.10",
                            )
                        )
                overflow = r.decls.get("overflow", "") + r.decls.get("overflow-y", "")
                if (
                    "hidden" in overflow
                    and _px(r.decls.get("height", "")) is not None
                    and TEXT_BOXES.match(re.split(r"[\s>+~:.#\[]+", r.selector.strip())[0] or "")
                ):
                    problems.append(
                        Problem(
                            "spacing",
                            f"{r.selector}: a fixed height with overflow hidden cuts off text a reader spaces out.",
                            "1.4.12",
                        )
                    )

        if not printing and contrast(link, text) < 3:
            plain = [
                r
                for r in active
                if _selects(r.selector, "a")
                and ":hover" not in r.selector
                and ":focus" not in r.selector
                and re.search(
                    r"(^|\s)none(\s|$|!)",
                    r.decls.get("text-decoration", "") + " " + r.decls.get("text-decoration-line", ""),
                )
            ]
            if plain:
                problems.append(
                    Problem(
                        "link_colour",
                        f"Links ({_hex(link)}) are {contrast(link, text):.2f}:1 against the text ({_hex(text)}) and "
                        "not underlined: keep the underline, or make them 3:1 apart.",
                        "1.4.1",
                    )
                )
    return _unique(problems)


def _unique(problems: list[Problem]) -> list[Problem]:
    seen, out = set(), []
    for p in problems:
        if (p.code, p.message) not in seen:
            seen.add((p.code, p.message))
            out.append(p)
    return out
