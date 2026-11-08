"""
Fetching one page someone pasted a link to, safely.

- http and https only, at most ``max_redirects`` redirects, each one checked again;
- every address a host resolves to must be public (no loopback, private, link-local, multicast or reserved
  ranges, so no cloud metadata endpoint). The check runs when the connection is made, on the address actually
  connected to, so a DNS answer that changes between check and connect (rebinding) gets nowhere;
- a timeout, a size cap and HTML only;
- an honest User-Agent. apply never pretends to be a browser and never works around a block: a 401, 403 or
  429, a CAPTCHA or a sign-in wall stops here and the person takes over.
- no proxy from the environment, no cookies kept between fetches.
"""

import asyncio
import ipaddress
import json
import socket
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import httpcore
import httpx

USER_AGENT = "apply/{version} (self-hosted; fetching a page a person pasted)"
HTML_TYPES = ("text/html", "application/xhtml+xml")
JSON_TYPES = ("application/json", "text/json")
XML_TYPES = ("application/xml", "text/xml", "application/rss+xml", "application/atom+xml")


class FetchError(Exception):
    """A page that could not or should not be fetched. ``code`` is stable; the message is for logs."""

    URL_NOT_ALLOWED = "URL_NOT_ALLOWED"
    ADDRESS_NOT_ALLOWED = "ADDRESS_NOT_ALLOWED"
    FAILED = "FETCH_FAILED"
    BLOCKED = "FETCH_BLOCKED"
    NOT_HTML = "FETCH_NOT_HTML"
    TOO_LARGE = "FETCH_TOO_LARGE"
    TOO_MANY_REDIRECTS = "FETCH_TOO_MANY_REDIRECTS"

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FetchConfig:
    version: str = "0"
    timeout: float = 10.0  # each step: connecting, each read
    total_timeout: float = 30.0  # the whole fetch, redirects included: a server trickling bytes can't hold it open
    max_bytes: int = 3_000_000  # a web page
    max_json_bytes: int = 30_000_000  # a job board's whole listing (some boards answer with several MB)
    max_redirects: int = 5
    allow_private: bool = False  # for tests that serve pages from this machine


@dataclass(frozen=True)
class Page:
    url: str  # where it ended up, after redirects
    status: int
    content_type: str
    html: str


# IPv6 prefixes that reach IPv4 addresses through a translator (NAT64): they could reach a private network.
TRANSLATED = (ipaddress.ip_network("64:ff9b::/96"), ipaddress.ip_network("64:ff9b:1::/48"))


def is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif any(ip in net for net in TRANSLATED):
            return False
    return ip.is_global and not ip.is_multicast and not ip.is_reserved


def check_url(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url)
    except (httpx.InvalidURL, TypeError) as exc:
        raise FetchError(FetchError.URL_NOT_ALLOWED, f"Not a URL: {url!r}") from exc
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise FetchError(FetchError.URL_NOT_ALLOWED, f"Only http(s) links can be fetched: {url!r}")
    if parsed.userinfo:
        raise FetchError(FetchError.URL_NOT_ALLOWED, "Links with a user name or password are not fetched")
    return parsed


class _GuardedBackend(httpcore.AsyncNetworkBackend):
    """Resolves the host itself and connects only to an address that passes the check."""

    def __init__(self, allow_private: bool):
        self._inner = httpcore.AnyIOBackend()
        self._allow_private = allow_private

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,  # noqa: ASYNC109 (httpcore's interface)
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise httpcore.ConnectError(f"Could not resolve {host}: {exc}") from exc
        addresses = list(dict.fromkeys(info[4][0] for info in infos))
        if not addresses:
            raise httpcore.ConnectError(f"{host} has no address")
        if not self._allow_private:
            refused = [a for a in addresses if not is_public_address(a)]
            if refused:
                raise _AddressRefused(f"{host} resolves to an address that is not public: {refused[0]}")
        last: Exception | None = None
        for address in addresses:
            try:
                return await self._inner.connect_tcp(
                    address, port, timeout=timeout, local_address=local_address, socket_options=socket_options
                )
            except httpcore.ConnectError as exc:
                last = exc
        raise last or httpcore.ConnectError(f"Could not connect to {host}")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


class _AddressRefused(httpcore.ConnectError):
    pass


class GuardedTransport(httpx.AsyncHTTPTransport):
    """httpx's transport, with its connection pool on the guarded backend (TLS still checks the real host name)."""

    def __init__(self, *, allow_private: bool = False):
        super().__init__(trust_env=False, retries=0)
        # httpx builds its pool in __init__ with no way to pass a network backend; replace it with one that has
        # ours. tests/unit/test_safe_fetch.py fails if this ever stops guarding connections.
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=httpx.create_ssl_context(trust_env=False),
            network_backend=_GuardedBackend(allow_private),
            max_connections=10,
            max_keepalive_connections=0,
        )


class Fetcher:
    def __init__(self, config: FetchConfig, *, transport: httpx.AsyncBaseTransport | None = None):
        self.config = config
        self._client = httpx.AsyncClient(
            transport=transport or GuardedTransport(allow_private=config.allow_private),
            timeout=httpx.Timeout(config.timeout),
            follow_redirects=False,
            trust_env=False,
            headers={
                "User-Agent": USER_AGENT.format(version=config.version),
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.1",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _within(self, url: str, work: Any) -> Any:
        try:
            async with asyncio.timeout(self.config.total_timeout):
                return await work
        except TimeoutError as exc:
            raise FetchError(FetchError.FAILED, f"{url} took too long") from exc

    async def fetch(self, url: str) -> Page:
        """A web page (HTML)."""
        return await self._within(url, self._get(url, HTML_TYPES, self.config.max_bytes))

    async def fetch_json(self, url: str) -> Any:
        """A public JSON API's answer (a job board's postings), with the same guards as a page."""
        page = await self._within(url, self._get(url, JSON_TYPES, self.config.max_json_bytes))
        try:
            return json.loads(page.html)
        except json.JSONDecodeError as exc:
            raise FetchError(FetchError.FAILED, f"{url} did not answer with JSON: {exc}") from exc

    async def fetch_xml(self, url: str) -> ElementTree.Element:
        """
        A public XML feed (board08's job feed), with the same guards as a page. One that declares a DTD or
        entities is refused: nothing in it is expanded or fetched.
        """
        page = await self._within(url, self._get(url, XML_TYPES, self.config.max_json_bytes))
        head = page.html[:4096]
        if "<!DOCTYPE" in head or "<!ENTITY" in page.html:
            raise FetchError(FetchError.FAILED, f"{url} declares a DTD or entities; not read")
        try:
            return ElementTree.fromstring(page.html)
        except ElementTree.ParseError as exc:
            raise FetchError(FetchError.FAILED, f"{url} did not answer with XML: {exc}") from exc

    async def post_json(self, url: str, body: dict[str, Any]) -> Any:
        """A public JSON API that's searched with a POST (Grants.gov). Same guards; a redirect isn't followed."""
        return await self._within(url, self._post_json(url, body))

    async def _post_json(self, url: str, body: dict[str, Any]) -> Any:
        current = check_url(url)
        try:
            async with self._client.stream(
                "POST", current, json=body, headers={"Accept": "application/json"}
            ) as response:
                if response.is_redirect:
                    raise FetchError(FetchError.FAILED, f"{current} redirected a search; not followed")
                page = await self._read(current, response, JSON_TYPES, self.config.max_json_bytes)
        except _AddressRefused as exc:
            raise FetchError(FetchError.ADDRESS_NOT_ALLOWED, str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise FetchError(FetchError.FAILED, f"{current} took too long") from exc
        except httpx.HTTPError as exc:
            cause = exc.__cause__ or exc.__context__
            if isinstance(cause, _AddressRefused):
                raise FetchError(FetchError.ADDRESS_NOT_ALLOWED, str(cause)) from exc
            raise FetchError(FetchError.FAILED, f"Could not post to {current}: {exc!r}") from exc
        try:
            return json.loads(page.html)
        except json.JSONDecodeError as exc:
            raise FetchError(FetchError.FAILED, f"{url} did not answer with JSON: {exc}") from exc

    async def _get(self, url: str, accept: tuple[str, ...], max_bytes: int) -> Page:
        current = check_url(url)
        for _hop in range(self.config.max_redirects + 1):
            try:
                async with self._client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError(FetchError.FAILED, f"Redirect from {current} without a Location")
                        current = check_url(urljoin(str(current), location))
                        continue
                    return await self._read(current, response, accept, max_bytes)
            except _AddressRefused as exc:
                raise FetchError(FetchError.ADDRESS_NOT_ALLOWED, str(exc)) from exc
            except httpx.TimeoutException as exc:
                raise FetchError(FetchError.FAILED, f"{current} took too long") from exc
            except httpx.HTTPError as exc:
                cause = exc.__cause__ or exc.__context__
                if isinstance(cause, _AddressRefused):
                    raise FetchError(FetchError.ADDRESS_NOT_ALLOWED, str(cause)) from exc
                raise FetchError(FetchError.FAILED, f"Could not fetch {current}: {exc!r}") from exc
        raise FetchError(FetchError.TOO_MANY_REDIRECTS, f"More than {self.config.max_redirects} redirects from {url}")

    async def _read(self, url: httpx.URL, response: httpx.Response, accept: tuple[str, ...], max_bytes: int) -> Page:
        if response.status_code in (401, 403, 407, 429, 451):
            raise FetchError(FetchError.BLOCKED, f"{url} answered {response.status_code}")
        if response.status_code >= 400:
            raise FetchError(FetchError.FAILED, f"{url} answered {response.status_code}")
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type and content_type not in accept:
            raise FetchError(FetchError.NOT_HTML, f"{url} is {content_type}, not {' or '.join(accept)}")
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise FetchError(FetchError.TOO_LARGE, f"{url} is {declared} bytes")
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > max_bytes:
                raise FetchError(FetchError.TOO_LARGE, f"{url} is over {max_bytes} bytes")
        encoding = response.charset_encoding or "utf-8"
        try:
            html = body.decode(encoding, errors="replace")
        except LookupError:
            html = body.decode("utf-8", errors="replace")
        return Page(url=str(url), status=response.status_code, content_type=content_type or accept[0], html=html)


def canonical_url(url: str) -> str:
    """The same posting under one name: no fragment, no tracking parameters, a lower-case host, no default port."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    port = parts.port
    if port and not ((parts.scheme == "http" and port == 80) or (parts.scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    query = "&".join(
        p
        for p in parts.query.split("&")
        if p and not p.lower().startswith(("utm_", "gclid=", "fbclid=", "mc_cid=", "mc_eid="))
    )
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return f"{parts.scheme.lower()}://{host}{path}" + (f"?{query}" if query else "")
