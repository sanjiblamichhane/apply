"""
Discovery against the real model, and (separately opt-in) against real public boards.

    APPLY_LIVE=1 uv run pytest tests/live -s                         the model scores postings
    APPLY_LIVE=1 APPLY_LIVE_SOURCES=1 uv run pytest tests/live -s  and each adapter fetches one real board

Real boards are asked once per run, well inside every source's terms. Which boards is yours to choose: any public
board works. Name them in APPLY_LIVE_BOARDS, as JSON {kind: [pack, config]}, for example
'{"board01": ["job", {"board": "<a company's board name>"}]}'. The public-sector feeds need no choice.
"""

import json
import os
import time

import pytest

from apply.libs.extract import FetchConfig, Fetcher
from apply.logic.matches import parse_score
from apply.packs import get_pack
from apply.packs.base import OpportunityInput, ProfileInput
from tests.api.helpers import PROFILE

LIVE_SOURCES = os.environ.get("APPLY_LIVE_SOURCES") == "1"
BOARDS: dict[str, tuple[str, dict[str, str]]] = {
    "contracts_finder": ("tender", {}),
    "grants_gov": ("grant", {"keyword": "health"}),
} | {kind: (pack, config) for kind, (pack, config) in json.loads(os.environ.get("APPLY_LIVE_BOARDS") or "{}").items()}


async def test_the_model_scores_a_clear_fit_higher_than_a_poor_one(live_model):
    pack = get_pack("job")
    profile = ProfileInput(name="Backend", summary=PROFILE["summary"], attributes=PROFILE["attributes"])

    async def score(title: str, description: str) -> int:
        prompt = pack.score_prompt(
            profile,
            OpportunityInput(
                title=title, issuer_name="Acme", attributes={"job_title": title, "description_markdown": description}
            ),
        )
        started = time.monotonic()
        value, reasons, _ = parse_score(
            await live_model.complete_json(prompt.text, pack.score_schema, purpose=prompt.purpose)
        )
        print(f"\n[live] {title}: {value} in {time.monotonic() - started:.1f}s; {reasons}")
        return value

    good = await score("Senior Backend Engineer", "Python, Django REST Framework, PostgreSQL, Celery. 5+ years.")
    poor = await score("Registered Nurse", "Registered nursing licence required. ICU experience, night shifts.")
    assert good >= 60 and poor <= 40 and good > poor
    await live_model.aclose()


@pytest.mark.skipif(not LIVE_SOURCES, reason="Fetches real public boards; set APPLY_LIVE_SOURCES=1.")
@pytest.mark.parametrize("kind", list(BOARDS))
async def test_each_adapter_reads_a_real_board(kind):
    pack, config = BOARDS[kind]
    adapter = get_pack(pack).source(kind)
    fetcher = Fetcher(FetchConfig(version="live-test"))
    try:
        listings = await adapter.fetch(fetcher, adapter.validate_config(config), adapter.default_base_url)
    finally:
        await fetcher.aclose()
    print(f"\n[live] {kind}: {len(listings)} postings; first: {listings[0].title if listings else '-'}")
    assert listings, f"{kind} answered but listed nothing"
    assert all(item.title and item.source_url.startswith("https://") for item in listings)
    # What the pack keeps is valid for the pack: the recorded shapes in the tests still match the real ones.
    for item in listings[:20]:
        get_pack(pack).validate_opportunity(item.attributes)
        assert item.issuer_name, f"{kind}: {item.title} has no issuer"
