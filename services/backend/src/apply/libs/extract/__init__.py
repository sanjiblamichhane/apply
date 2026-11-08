"""Text to read: an opportunity's off the web (a safe fetch, JSON-LD, HTML as text), and an uploaded document's."""

from .document import Document, DocumentError, document_text
from .fetch import FetchConfig, Fetcher, FetchError, Page, canonical_url, check_url
from .html import looks_like_a_wall, page_text, title, to_markdown
from .jsonld import find_nodes, text

__all__ = [
    "Document",
    "DocumentError",
    "FetchConfig",
    "FetchError",
    "Fetcher",
    "Page",
    "canonical_url",
    "check_url",
    "document_text",
    "find_nodes",
    "looks_like_a_wall",
    "page_text",
    "text",
    "title",
    "to_markdown",
]
