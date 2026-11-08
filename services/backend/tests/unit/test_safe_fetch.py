"""Fetching a pasted link: only public addresses, only web pages, an honest User-Agent, no getting round a block."""

import pytest

from apply.libs.extract import FetchConfig, Fetcher, FetchError, canonical_url
from apply.libs.extract.fetch import is_public_address


@pytest.fixture
async def guarded():
    fetcher = Fetcher(FetchConfig(version="test", timeout=3, allow_private=False))
    yield fetcher
    await fetcher.aclose()


@pytest.fixture
async def local(site):
    fetcher = Fetcher(FetchConfig(version="test", timeout=3, max_bytes=50_000, allow_private=True))
    yield fetcher
    await fetcher.aclose()


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "::1",
        "fe80::1",
        "fc00::1",
        "::ffff:127.0.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "240.0.0.1",
        "64:ff9b::7f00:1",  # NAT64 to 127.0.0.1
        "64:ff9b::a01:203",  # NAT64 to 10.1.2.3
        "64:ff9b:1::1",
    ],
)
def test_addresses_that_are_not_public(address):
    assert not is_public_address(address)


@pytest.mark.parametrize("address", ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses(address):
    assert is_public_address(address)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/x",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "not a url",
        "http://user:pass@example.com/",
        "http:///nohost",
    ],
)
async def test_only_plain_http_links(guarded, url):
    with pytest.raises(FetchError) as caught:
        await guarded.fetch(url)
    assert caught.value.code == FetchError.URL_NOT_ALLOWED


async def test_this_machine_is_refused_at_connect_time(guarded, site):
    # The guard sits in the connection itself (it replaces httpx's pool); if httpx ever stops using it, this fails.
    site.add("/job", "<html>hi</html>")
    with pytest.raises(FetchError) as caught:
        await guarded.fetch(f"{site.url}/job")
    assert caught.value.code == FetchError.ADDRESS_NOT_ALLOWED
    assert site.hits == []


async def test_a_name_that_resolves_to_this_machine_is_refused(guarded, site):
    with pytest.raises(FetchError) as caught:
        await guarded.fetch(f"http://localhost:{site.url.rsplit(':', 1)[1]}/job")
    assert caught.value.code == FetchError.ADDRESS_NOT_ALLOWED


async def test_a_redirect_is_checked_again(local, site):
    site.add("/start", status=302, headers={"location": "ftp://example.com/x"})
    with pytest.raises(FetchError) as caught:
        await local.fetch(f"{site.url}/start")
    assert caught.value.code == FetchError.URL_NOT_ALLOWED


async def test_redirects_are_followed_a_few_times_only(local, site):
    site.add("/a", status=301, headers={"location": "/b"})
    site.add("/b", "<html><h1>Here</h1></html>")
    page = await local.fetch(f"{site.url}/a")
    assert page.url.endswith("/b") and "Here" in page.html
    site.add("/loop", status=302, headers={"location": "/loop"})
    with pytest.raises(FetchError) as caught:
        await local.fetch(f"{site.url}/loop")
    assert caught.value.code == FetchError.TOO_MANY_REDIRECTS


@pytest.mark.parametrize("status", [401, 403, 429])
async def test_a_block_stops_here(local, site, status):
    site.add("/blocked", "go away", status=status)
    with pytest.raises(FetchError) as caught:
        await local.fetch(f"{site.url}/blocked")
    assert caught.value.code == FetchError.BLOCKED
    assert len(site.hits) == 1  # asked once, never retried with other headers


async def test_only_web_pages_and_not_too_big(local, site):
    site.add("/file.pdf", b"%PDF-1.7", content_type="application/pdf")
    with pytest.raises(FetchError) as caught:
        await local.fetch(f"{site.url}/file.pdf")
    assert caught.value.code == FetchError.NOT_HTML
    site.add("/big", "x" * 60_000)
    with pytest.raises(FetchError) as caught:
        await local.fetch(f"{site.url}/big")
    assert caught.value.code == FetchError.TOO_LARGE


async def test_the_user_agent_is_honest(local, site):
    site.add("/job", "<html>ok</html>")
    await local.fetch(f"{site.url}/job")
    agent = site.hits[-1][1]["user-agent"]
    assert agent.startswith("apply/test (self-hosted;")  # its own name, never a browser's


async def test_a_server_error_is_a_failed_fetch(local, site):
    site.add("/oops", "boom", status=500)
    with pytest.raises(FetchError) as caught:
        await local.fetch(f"{site.url}/oops")
    assert caught.value.code == FetchError.FAILED


@pytest.mark.parametrize(
    ("url", "canonical"),
    [
        ("https://Jobs.Example.com/role/42/?utm_source=x&gh_jid=7#apply", "https://jobs.example.com/role/42?gh_jid=7"),
        ("http://example.com:80/a", "http://example.com/a"),
        ("https://example.com:8443/a?b=1", "https://example.com:8443/a?b=1"),
        ("https://example.com", "https://example.com/"),
    ],
)
def test_canonical_urls(url, canonical):
    assert canonical_url(url) == canonical


async def test_a_boards_json_may_be_bigger_than_a_page_but_not_unbounded(site):
    fetcher = Fetcher(FetchConfig(version="test", max_bytes=50_000, max_json_bytes=200_000, allow_private=True))
    site.add("/board.json", '{"jobs": [' + ",".join(['{"title": "x"}'] * 6000) + "]}", content_type="application/json")
    assert len((await fetcher.fetch_json(f"{site.url}/board.json"))["jobs"]) == 6000  # ~90 KB: over a page's cap
    site.add("/huge.json", "[" + ",".join(["1"] * 150_000) + "]", content_type="application/json")
    with pytest.raises(FetchError) as caught:
        await fetcher.fetch_json(f"{site.url}/huge.json")
    assert caught.value.code == FetchError.TOO_LARGE
    site.add("/page.html", "<html>hi</html>")
    with pytest.raises(FetchError) as caught:
        await fetcher.fetch_json(f"{site.url}/page.html")
    assert caught.value.code == FetchError.NOT_HTML
    await fetcher.aclose()


async def test_a_server_that_trickles_bytes_cant_hold_a_fetch_open():
    """Security review: each read may be quick, but the whole fetch still has a deadline."""
    import asyncio
    import time

    async def trickle(reader, writer):
        await reader.readline()
        writer.write(b"HTTP/1.1 200 OK\r\ncontent-type: text/html\r\n\r\n")
        try:
            for _ in range(100):
                writer.write(b"<p>")
                await writer.drain()
                await asyncio.sleep(0.1)
        except ConnectionError:
            pass
        writer.close()

    server = await asyncio.start_server(trickle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    fetcher = Fetcher(FetchConfig(version="test", timeout=2, total_timeout=0.5, allow_private=True))
    started = time.monotonic()
    try:
        with pytest.raises(FetchError) as raised:
            await fetcher.fetch(f"http://127.0.0.1:{port}/slow")
        assert raised.value.code == FetchError.FAILED and time.monotonic() - started < 3
    finally:
        await fetcher.aclose()
        server.close()
