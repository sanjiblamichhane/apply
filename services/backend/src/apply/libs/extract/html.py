"""A web page as text: markdown-ish for descriptions, plain for prompts, and a few signs of a page that is a wall."""

import re

from bs4 import BeautifulSoup, Tag

_NOISE = ["script", "style", "noscript", "template", "svg", "nav", "footer", "header", "aside", "form", "iframe"]
_BLOCK = ["p", "div", "section", "article", "br", "tr", "table"]
_WALL_SIGNS = (
    "captcha",
    "are you a robot",
    "verify you are human",
    "access denied",
    "enable javascript",
    "please sign in to continue",
    "log in to continue",
    "sign in to view",
    "unusual traffic",
)


def to_markdown(html: str) -> str:
    """HTML (a description, usually) to light markdown: headings, list items and paragraphs kept."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.insert(0, "# " if tag.name == "h1" else "## ")
        tag.append("\n\n")
    for tag in soup.find_all("li"):
        tag.insert(0, "- ")
        tag.append("\n")
    for tag in soup.find_all(["strong", "b"]):
        if tag.get_text(strip=True):
            tag.insert(0, "**")
            tag.append("**")
    for tag in soup.find_all(["p", "section", "article", "table", "ul", "ol"]):
        tag.append("\n\n")
    for tag in soup.find_all(["div", "br", "tr"]):
        tag.append("\n")
    return _tidy(soup.get_text())


def page_text(html: str, *, limit: int = 40_000) -> str:
    """The readable text of a whole page, without navigation, scripts and forms, cut to ``limit`` characters."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_NOISE):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    for tag in main.find_all(_BLOCK + ["li", "h1", "h2", "h3", "h4"]) if isinstance(main, Tag) else []:
        tag.append("\n")
    return _tidy(main.get_text())[:limit]


def title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(" ", strip=True)[:300]
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return str(og["content"]).strip()[:300]
    return soup.title.get_text(strip=True)[:300] if soup.title else ""


def looks_like_a_wall(text: str) -> bool:
    """A CAPTCHA, a sign-in wall or a bot check rather than the page itself (checked on short pages only)."""
    head = text[:2000].lower()
    return any(sign in head for sign in _WALL_SIGNS)


def _tidy(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
