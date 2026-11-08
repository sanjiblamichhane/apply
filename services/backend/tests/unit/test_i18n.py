"""Every string the backend owns, in English, Nepali and Spanish."""

import re

import pytest

from apply.api.schemas import Label
from apply.i18n import CATALOGUES, CLI, LOCALES, SOURCE, cli_locale, t
from apply.packs import all_packs
from apply.packs.base import ACTION_LABELS, CATEGORY_LABELS, PROFILE_KIND_LABELS

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def every_label():
    yield from (("cli." + k, v) for k, v in CLI.items())
    yield from (("category." + k, v) for k, v in CATEGORY_LABELS.items())
    yield from (("action." + k, v) for k, v in ACTION_LABELS.items())
    yield from (("profile_kind." + k, v) for k, v in PROFILE_KIND_LABELS.items())
    for pack in all_packs().values():
        yield from pack.labels().items()


@pytest.mark.parametrize(("key", "entry"), list(every_label()), ids=lambda v: v if isinstance(v, str) else "")
def test_every_language_is_there(key, entry):
    assert set(entry) == set(LOCALES), key
    for locale in LOCALES:
        assert entry[locale].strip(), f"{key} has no {locale}"
    assert DEVANAGARI.search(entry["ne"]), f"{key}: the Nepali is not in Devanagari"


def test_placeholders_match_between_languages():
    for key, entry in every_label():
        for locale in LOCALES:
            assert set(re.findall(r"\{(\w+)\}", entry["en"])) == set(re.findall(r"\{(\w+)\}", entry[locale])), key


def test_each_catalogue_holds_only_strings_the_backend_has():
    list(every_label())  # every label made, so SOURCE is complete
    for code, catalogue in CATALOGUES.items():
        assert catalogue, f"no catalogue for {code}"
        assert sorted(set(catalogue) - SOURCE) == [], f"{code}.json has English the backend no longer uses"


def test_the_api_label_has_every_language():
    assert set(Label.model_fields) == set(LOCALES)


def test_every_category_and_action_used_by_a_pack_has_a_label():
    for pack in all_packs().values():
        for stage in pack.pipeline.stages:
            assert stage.category in CATEGORY_LABELS and stage.action_type in ACTION_LABELS
        for kind in pack.profile_kinds:
            assert kind in PROFILE_KIND_LABELS


def test_the_command_line_speaks_nepali_when_asked(monkeypatch):
    monkeypatch.setenv("APPLY_LANG", "ne")
    assert cli_locale() == "ne"
    assert t("migrate.done") == "डेटाबेस अद्यावधिक छ।"
    monkeypatch.setenv("APPLY_LANG", "en")
    assert t("init.done", email="a@b.c").startswith("Created the owner account for a@b.c")


def test_the_command_line_speaks_the_systems_language(monkeypatch):
    monkeypatch.delenv("APPLY_LANG", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.setenv("LANG", "es_MX.UTF-8")
    assert cli_locale() == "es"
    assert t("migrate.done") != CLI["migrate.done"]["en"]
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert cli_locale() == "en"
