"""Reading schema.org JSON-LD from a page: every node of the wanted types, wherever the page put it."""

import json
from collections.abc import Iterator
from typing import Any

from bs4 import BeautifulSoup


def _walk(value: Any) -> Iterator[dict[str, Any]]:
    """Every object in a JSON-LD document: top level, in lists, and in @graph."""
    if isinstance(value, list):
        for item in value:
            yield from _walk(item)
    elif isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from _walk(graph)


def _types(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    values = raw if isinstance(raw, list) else [raw]
    # "JobPosting", "schema:JobPosting" and "https://schema.org/JobPosting" are the same type.
    return {str(v).rsplit("/", 1)[-1].rsplit(":", 1)[-1] for v in values if v}


def find_nodes(html: str | BeautifulSoup, types: set[str]) -> list[dict[str, Any]]:
    soup = html if isinstance(html, BeautifulSoup) else BeautifulSoup(html, "html.parser")
    found: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text()
        if not raw or not raw.strip():
            continue
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        found.extend(node for node in _walk(data) if _types(node) & types)
    return found


def text(value: Any) -> str:
    """A JSON-LD value as plain text: a string, the name of an object, or the first of a list."""
    if value is None:
        return ""
    if isinstance(value, list):
        return text(value[0]) if value else ""
    if isinstance(value, dict):
        return text(value.get("name") or value.get("@value") or "")
    return str(value).strip()
