"""
The tender, grant and contract packs on their own, and the rule that makes them possible: the engine names no
pack. A new pack is only a pack.
"""

import ast
import re
from datetime import date
from pathlib import Path

import pytest

from apply.packs import all_packs, get_pack
from apply.packs.base import OpportunityInput, ProfileInput

NEW = ["tender", "grant", "contract"]
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


@pytest.mark.parametrize("key", list(all_packs()))
def test_every_field_says_what_it_is_in_both_languages(key):
    pack = get_pack(key)
    for model in (pack.profile_model, pack.opportunity_model):
        schema = model.model_json_schema()
        props = dict(schema["properties"])
        for definition in schema.get("$defs", {}).values():
            props |= definition.get("properties", {})
        for name, prop in props.items():
            label = prop.get("x-label")
            assert label and label["en"] and DEVANAGARI.search(label["ne"]), f"{key}: {model.__name__}.{name}"


@pytest.mark.parametrize("key", NEW)
def test_prompts_are_filled_and_hold_to_the_profile(key):
    pack = get_pack(key)
    profile = ProfileInput(name="Himal Works", summary="We build software.", attributes={}, tone_instructions="Plain.")
    opp = OpportunityInput(
        title="Case management", issuer_name="Example City Council", attributes={pack.title_field: "Case management"}
    )
    prompts = [
        pack.document_prompt(d.key, profile, opp, date(2026, 10, 26)) for d in pack.document_types if d.generatable
    ]
    prompts += [
        pack.score_prompt(profile, opp),
        pack.extraction_prompt("Some notice"),
        pack.claims_prompt("# Doc", profile),
    ]
    for prompt in prompts:
        assert "{{" not in prompt.text, prompt.text[:200]
    for prompt in prompts[:2]:
        assert "THE MOST IMPORTANT RULE: use only facts from" in prompt.text and "Never invent" in prompt.text
        assert "[CONFIRM:" in prompt.text
        assert "Plain." in prompt.text  # the person's tone


@pytest.mark.parametrize("key", NEW)
def test_reading_a_notice_keeps_only_the_packs_fields(key):
    pack = get_pack(key)
    schema = pack.extraction_schema()
    assert set(schema["required"]) <= set(pack.opportunity_model.model_fields)
    data = {k: f"  {k} value " for k in schema["properties"]} | {"surprise": "dropped"}
    if "workplace" in data:
        data["workplace"] = "on the moon"  # not one of its values
    extracted = pack.from_extraction(data)
    assert extracted.title == f"{pack.title_field} value"
    assert extracted.issuer_name == f"{pack.issuer_field} value"
    assert "surprise" not in extracted.attributes
    if "workplace" in extracted.attributes:
        assert extracted.attributes["workplace"] == ""


def test_the_same_notice_twice_is_one():
    tender = get_pack("tender")
    a = tender.dedupe_key("Example City Council", "Case Management Software", {"reference": "ECC-0142"})
    b = tender.dedupe_key("example city council", "case management software!", {"reference": "ECC 0142"})
    assert a == b
    assert a != tender.dedupe_key("Example City Council", "Case Management Software", {"reference": "ECC-0143"})


def test_search_options_fit_each_pack():
    assert get_pack("job").search_options == {"locations", "remote_only", "needs_sponsorship"}
    assert get_pack("tender").search_options == {"locations"}
    assert get_pack("contract").search_options == {"locations", "remote_only"}
    contract = get_pack("contract").searchable("Site", {"title": "Site", "workplace": "remote"})
    assert contract.remote and contract.sponsorship == ""


# ── the engine names no pack ─────────────────────────────────────────────────

ENGINE = Path(__file__).parents[2] / "src" / "apply"
ENGINE_PARTS = ["logic", "contract", "store", "libs", "worker.py", "app.py", "runtime.py", "settings.py"]


def _engine_strings() -> list[tuple[str, str]]:
    found = []
    for part in ENGINE_PARTS:
        path = ENGINE / part
        for file in [path] if path.is_file() else sorted(path.rglob("*.py")):
            if "migrations" in file.parts:
                continue  # history: what the tables were called then
            tree = ast.parse(file.read_text(encoding="utf-8"))
            docstrings = {
                id(node.body[0].value)
                for node in ast.walk(tree)
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
            }
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                    found.append((str(file.relative_to(ENGINE)), node.value))
    return found


def test_the_engine_names_no_pack_and_no_packs_field():
    """Everything pack-specific lives in packs/: a new pack needs no change here (plan principle 5)."""
    names: set[str] = set()
    for pack in all_packs().values():
        names.add(pack.key)
        names |= {d.key for d in pack.document_types}
        for model in (pack.profile_model, pack.opportunity_model):
            names |= {n for n in model.model_fields if "_" in n}  # the distinctive ones: job_title, legal_name…
        names |= {a.kind for a in pack.sources}
    offending = [(f, v) for f, v in _engine_strings() if v in names]
    assert offending == [], offending
