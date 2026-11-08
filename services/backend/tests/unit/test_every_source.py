"""
What every source must do, checked once for all of them against its recording (tests/support/recordings.py),
over real HTTP from the local test site. A new source needs only its recording to be held to all of this.
"""

from urllib.parse import urlsplit

import pytest

from apply.libs.extract import FetchConfig, Fetcher
from apply.packs import all_packs
from tests.support.recordings import RECORDINGS

SOURCES = [(pack.key, adapter) for pack in all_packs().values() for adapter in pack.sources]


class OnlyTheSite(Fetcher):
    """The fetcher, refusing anything but the test site: a source never reaches the real platform here."""

    def __init__(self, site_url: str) -> None:
        super().__init__(FetchConfig(version="test", allow_private=True))
        self.site_url = site_url
        self.asked: list[str] = []

    def _only(self, url: str) -> None:
        assert url.startswith(self.site_url), f"asked {url}, not the test site"
        self.asked.append(url)

    async def fetch_json(self, url):
        self._only(url)
        return await super().fetch_json(url)

    async def fetch_xml(self, url):
        self._only(url)
        return await super().fetch_xml(url)

    async def post_json(self, url, body):
        self._only(url)
        return await super().post_json(url, body)

    async def fetch(self, url):
        self._only(url)
        return await super().fetch(url)


def test_every_source_has_a_recording():
    missing = [adapter.kind for _, adapter in SOURCES if adapter.kind not in RECORDINGS]
    assert not missing, f"add a recording for {missing} to tests/support/recordings.py"


@pytest.mark.parametrize(("pack_key", "adapter"), SOURCES, ids=[a.kind for _, a in SOURCES])
async def test_a_source_reads_its_platform_into_the_pack(pack_key, adapter, site):
    recording = RECORDINGS[adapter.kind]
    assert recording.pack == pack_key
    config = adapter.validate_config(recording.config)
    assert adapter.display_name(config)
    recording.serve(site)
    fetcher = OnlyTheSite(site.url)
    try:
        listings = await adapter.fetch(fetcher, config, site.url)
    finally:
        await fetcher.aclose()

    assert len(listings) == recording.listings, [x.title for x in listings]
    assert fetcher.asked, "it asked for nothing"
    pack = all_packs()[pack_key]
    refs = [x.ref for x in listings]
    assert all(refs) and len(set(refs)) == len(refs), refs
    for listing in listings:
        assert listing.title.strip() and listing.issuer_name.strip(), listing
        for url in (listing.source_url, listing.apply_url):
            if url.startswith(site.url):
                continue  # made from the base address: the platform's own https one outside the tests
            parts = urlsplit(url)
            assert parts.scheme == "https" and parts.hostname, f"{adapter.kind}: {url} isn't a public https link"
        assert pack.validate_opportunity(listing.attributes) == listing.attributes
        assert listing.posted_at is None or listing.posted_at.tzinfo is not None


@pytest.mark.parametrize(("pack_key", "adapter"), SOURCES, ids=[a.kind for _, a in SOURCES])
def test_a_source_keeps_to_its_terms(pack_key, adapter):
    assert adapter.min_interval_hours >= 1, "no source asks more than hourly"
    # A source whose terms ask to be named says so in what it shows ("via …"), and has the name to show.
    if "via" in adapter.terms["en"]:
        assert adapter.attribution, f"{adapter.kind}: its terms ask to be named; set attribution"
    for spec in adapter.config_fields:
        assert spec.pattern.startswith("^") and spec.pattern.endswith("$"), f"{adapter.kind}.{spec.key}: anchor it"
    assert adapter.default_base_url.startswith("https://")
    for language in ("en", "ne", "es"):
        assert adapter.label.get(language) and adapter.description.get(language) and adapter.terms.get(language)
