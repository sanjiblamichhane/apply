"""
The text of an uploaded document (a resume, a capability statement): PDF, .docx, or plain text/Markdown.

A file someone uploads may be hostile, so each kind is read by what its bytes are (never its name or the type the
browser claims), with safe parsers only: ``pypdf`` (pure Python; no JavaScript, forms or embedded files are
touched, and no more than ``MAX_PAGES`` pages), the standard library for .docx (its document.xml only, size-checked
before it's unpacked, and refused if it declares entities), and UTF-8/UTF-16 for text. Nothing runs, nothing is
fetched, and nothing is written to disk.

    found = document_text(data)  # Document(kind="pdf", text="Sam Rai\\n…") or DocumentError
"""

import io
import re
import zipfile
from dataclasses import dataclass
from typing import Literal
from xml.etree import ElementTree

MAX_TEXT = 60_000  # characters kept
MAX_PAGES = 40
MAX_XML = 20_000_000  # a .docx's document.xml, unpacked
MIN_TEXT = 40  # less than this is a scan or an empty file, not a document

Kind = Literal["pdf", "docx", "text"]
EXTENSIONS: dict[Kind, str] = {"pdf": ".pdf", "docx": ".docx", "text": ".txt"}
CONTENT_TYPES: dict[Kind, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text": "text/plain; charset=utf-8",
}
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentError(Exception):
    def __init__(self, reason: Literal["unsupported", "no_text"], detail: str) -> None:
        self.reason = reason
        super().__init__(detail)


@dataclass(frozen=True)
class Document:
    kind: Kind
    text: str


def document_text(data: bytes) -> Document:
    """The document's text, tidied and at most MAX_TEXT characters; DocumentError if it can't be read."""
    if data.startswith(b"%PDF-"):
        kind: Kind = "pdf"
        text = _pdf(data)
    elif data.startswith(b"PK\x03\x04"):
        kind, text = "docx", _docx(data)
    else:
        kind, text = "text", _plain(data)
    text = _tidy(text)
    if len(text) < MIN_TEXT:
        raise DocumentError("no_text", f"The {kind} has no text to read (a scan, or empty)")
    return Document(kind=kind, text=text[:MAX_TEXT])


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise DocumentError("unsupported", "The PDF is protected by a password")
        parts: list[str] = []
        size = 0
        for page in reader.pages[:MAX_PAGES]:
            part = page.extract_text() or ""
            parts.append(part)
            size += len(part)
            if size > MAX_TEXT:
                break
        return "\n\n".join(parts)
    except DocumentError:
        raise
    except (PyPdfError, ValueError, KeyError, TypeError, OSError, RecursionError) as exc:
        raise DocumentError("unsupported", f"The PDF couldn't be read: {type(exc).__name__}") from exc


def _docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            try:
                info = archive.getinfo("word/document.xml")
            except KeyError:
                raise DocumentError("unsupported", "A zip file, but not a .docx document") from None
            if info.file_size > MAX_XML:
                raise DocumentError("unsupported", "The .docx document is too large to read")
            with archive.open(info) as part:
                xml = part.read(MAX_XML + 1)
    except zipfile.BadZipFile as exc:
        raise DocumentError("unsupported", "The .docx document is damaged") from exc
    if len(xml) > MAX_XML or b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
        raise DocumentError("unsupported", "The .docx document isn't one apply can read")
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise DocumentError("unsupported", "The .docx document is damaged") from exc
    lines: list[str] = []
    for paragraph in root.iter(f"{_W}p"):
        words: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{_W}t" and node.text:
                words.append(node.text)
            elif node.tag == f"{_W}tab":
                words.append("\t")
            elif node.tag in (f"{_W}br", f"{_W}cr"):
                words.append("\n")
        bullet = paragraph.find(f"{_W}pPr/{_W}numPr") is not None
        line = "".join(words)
        lines.append(f"- {line}" if bullet and line.strip() else line)
    return "\n".join(lines)


def _plain(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError as exc:
            raise DocumentError("unsupported", "The text isn't UTF-16") from exc
    if b"\x00" in data[:4096]:
        raise DocumentError("unsupported", "Not a PDF, .docx document or text file")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentError("unsupported", "The text isn't UTF-8") from exc


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _tidy(text: str) -> str:
    text = _CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = re.sub(r"[ \t\u00a0]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
