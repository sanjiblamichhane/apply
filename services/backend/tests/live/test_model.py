"""
Checks against the real model: is it there, does it hold to a schema, is thinking really off, is the context big
enough, and how long one score takes on this machine (printed, as it sets the daily match cap).
"""

import json
import time

from .conftest import MODEL, WRITING_MODEL

FIT_SCHEMA = {
    "type": "object",
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "reasons": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "dealbreakers": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["fit_score", "reasons", "dealbreakers"],
}
POSTING = (
    "Senior Backend Engineer, remote. Python, Django, PostgreSQL, Celery, Redis. 5+ years building APIs. "
    "Nice to have: React."
)
PROFILE = "Six years of Python and Django, PostgreSQL, Celery, some React. Based in Kathmandu, open to remote."
MAX_SECONDS_PER_SCORE = 60


async def test_the_model_is_reachable_and_there(live_model):
    check = await live_model.check()
    assert check.reachable, f"No model server answered at {check.base_url}: {check.error}"
    assert not check.missing, f"Not on the model server: {list(check.missing)}. Download them there first."
    print(f"\n[live] server {check.version}; {MODEL}{' and ' + WRITING_MODEL if WRITING_MODEL else ''} ready")
    await live_model.aclose()


async def test_a_score_holds_to_the_schema_quickly_and_without_thinking_aloud(live_model):
    started = time.monotonic()
    reply = await live_model.chat(
        f"Score how well this candidate fits the job, 0-100.\n\nJob: {POSTING}\n\nCandidate: {PROFILE}",
        purpose="score",
        json_schema=FIT_SCHEMA,
    )
    seconds = time.monotonic() - started
    assert "<think>" not in reply.text, "Thinking is on: the reply contains the model's reasoning."
    data = json.loads(reply.text)
    assert isinstance(data["fit_score"], int) and 0 <= data["fit_score"] <= 100
    assert isinstance(data["reasons"], list) and data["reasons"]
    assert isinstance(data["dealbreakers"], list)
    assert data["fit_score"] >= 50, data  # a clear match: the cheapest sign it read the prompt
    print(f"\n[live] one fit score took {seconds:.1f}s on {MODEL} (score {data['fit_score']})")
    assert seconds < MAX_SECONDS_PER_SCORE
    await live_model.aclose()


async def test_the_context_is_large_enough_for_a_long_posting(live_model):
    # About 8,000 tokens of filler after the instruction. With a server's usual default context the start of the prompt
    # is silently dropped and the model never sees the instruction.
    filler = "This paragraph describes the company's history and benefits in detail. " * 600
    reply = await live_model.chat(
        "Reply with exactly the word BANANA and nothing else.\n\n"
        + filler
        + "\n\nRemember the instruction at the top.",
        purpose="check",
    )
    assert "BANANA" in reply.text.upper(), "The start of a long prompt was lost; raise APPLY_LLM_NUM_CTX."
    await live_model.aclose()
