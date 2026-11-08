"""
The strings the backend owns, in every language apply speaks: pack labels (packs/*/labels.py) and the command
line.

English and Nepali are written next to each other in the code (``label("Legal name", "कानुनी नाम")``). Every other
language is a catalogue in ``locales/<code>.json`` that maps the English to its translation, as gettext does, so a
new language is one file and a line in ``LANGUAGES`` with no change to the packs. The web app has its own dictionary
for its screens and for error codes; this one covers only what the backend shows or sends.
tests/unit/test_i18n.py fails on a missing or empty translation, or a placeholder that differs from the English.
Every language but English is a first draft for a native speaker to review.
"""

import json
import os
from pathlib import Path
from typing import Literal, get_args

# English, Nepali and Spanish, by ISO 639-1 code: the same list as packages/i18n (its tests compare the two).
Locale = Literal["en", "ne", "es"]
LOCALES: tuple[Locale, ...] = get_args(Locale)

# One string in every language: {"en": …, "ne": …, "es": …}. English is always there; a label stored before a
# language was added may lack it, and a reader then sees the English.
Label = dict[str, str]

LOCALES_DIR = Path(__file__).parent / "locales"


def _catalogue(code: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{code}.json"
    return json.loads(path.read_text("utf-8")) if path.exists() else {}


# English → translation, for each language that isn't written inline.
CATALOGUES: dict[str, dict[str, str]] = {code: _catalogue(code) for code in LOCALES if code not in ("en", "ne")}

# Every English string a label was made from, so tests (and translators) can see what each catalogue needs.
SOURCE: set[str] = set()


def label(en: str, ne: str) -> Label:
    SOURCE.add(en)
    found: Label = {"en": en, "ne": ne}
    for code, catalogue in CATALOGUES.items():
        if en in catalogue:
            found[code] = catalogue[en]
    return found


def is_locale(value: object) -> bool:
    return isinstance(value, str) and value in LOCALES


# The command line (apply init, migrate, worker, serve, check-model).
CLI: dict[str, Label] = {
    "init.email": label("Your email: ", "तपाईंको इमेल: "),
    "init.password": label("Choose a password (at least 12 characters): ", "पासवर्ड छान्नुहोस् (कम्तीमा १२ अक्षर): "),
    "init.password_again": label("The same password again: ", "उही पासवर्ड फेरि: "),
    "init.password_mismatch": label(
        "The passwords are not the same. Nothing was created.", "दुवै पासवर्ड मिलेनन्। केही पनि बनाइएन।"
    ),
    "init.password_short": label(
        "The password needs at least 12 characters. Nothing was created.",
        "पासवर्डमा कम्तीमा १२ अक्षर चाहिन्छ। केही पनि बनाइएन।",
    ),
    "init.owner_exists": label(
        "apply already has an owner. Nothing was changed.", "apply को मालिक पहिल्यै छ। केही पनि परिवर्तन गरिएन।"
    ),
    "init.done": label(
        "Created the owner account for {email}. Sign in at the web app.",
        "{email} को लागि मालिक खाता बनाइयो। वेब एपमा साइन इन गर्नुहोस्।",
    ),
    "demo.has_accounts": label(
        "This database has accounts already, so no demo was made. Use an empty database, or add --force to put the "
        "demo into the account given with --email.",
        "यो डेटाबेसमा पहिल्यै खाताहरू छन्, त्यसैले डेमो बनाइएन। खाली डेटाबेस प्रयोग गर्नुहोस्, वा --email ले दिएको "
        "खातामा डेमो राख्न --force थप्नुहोस्।",
    ),
    "demo.done": label("The demo is ready. Sign in as {email}.", "डेमो तयार छ। {email} भएर साइन इन गर्नुहोस्।"),
    "migrate.done": label("The database is up to date.", "डेटाबेस अद्यावधिक छ।"),
    "db.not_ready": label(
        "The database is not ready. Start it (compose.yml's postgres service), then run: apply migrate",
        "डेटाबेस तयार छैन। यसलाई सुरु गर्नुहोस् (compose.yml को postgres सेवा), अनि चलाउनुहोस्: apply migrate",
    ),
    "worker.started": label(
        "Worker {name} is taking {queues} jobs, {concurrency} at a time. Stop with Ctrl+C.",
        "वर्कर {name} ले {queues} काम लिँदैछ, एक पटकमा {concurrency}। रोक्न Ctrl+C थिच्नुहोस्।",
    ),
    "worker.stopped": label("Worker stopped.", "वर्कर रोकियो।"),
    "model.ok": label(
        "The model answers at {url}: {models} ready, context {num_ctx} tokens.",
        "मोडेलले {url} मा जवाफ दिन्छ: {models} तयार, सन्दर्भ {num_ctx} टोकन।",
    ),
    "model.missing": label(
        "The model server answers at {url}, but doesn't have these models: {models}. Download them there first.",
        "मोडेल सर्भरले {url} मा जवाफ दिन्छ, तर यसमा यी मोडेलहरू छैनन्: {models}। पहिले त्यहाँ डाउनलोड गर्नुहोस्।",
    ),
    "model.ok_server": label(
        "The model answers at {url}: {models} ready (the server sets the context size).",
        "मोडेलले {url} मा जवाफ दिन्छ: {models} तयार (सन्दर्भको आकार सर्भरले तोक्छ)।",
    ),
    "models.in_use.chosen": label(
        "In use: {model} at {url}, chosen in Settings → Model.",
        "प्रयोगमा: {url} मा {model}, सेटिङहरू → मोडेलमा छानिएको।",
    ),
    "models.in_use.settings": label(
        "In use: {model} at {url}, from the settings (.env).",
        "प्रयोगमा: {url} मा {model}, सेटिङ (.env) बाट।",
    ),
    "models.none": label(
        "No model server answers on this machine. Start your local model server, then look again.",
        "यो मेसिनमा कुनै मोडेल सर्भरले जवाफ दिँदैन। आफ्नो स्थानीय मोडेल सर्भर सुरु गर्नुहोस्, अनि फेरि हेर्नुहोस्।",
    ),
    "models.loaded": label("loaded", "लोड भएको"),
    "models.embedding": label("embeddings only: can't be chosen", "इम्बेडिङ मात्र: छान्न मिल्दैन"),
    "model.unreachable": label(
        "Nothing answers at {url}. Is the model server running?", "{url} मा कसैले जवाफ दिएन। के मोडेल सर्भर चलिरहेको छ?"
    ),
    "password.email": label("The account's email: ", "खाताको इमेल: "),
    "password.choose": label("The new password (at least 12 characters): ", "नयाँ पासवर्ड (कम्तीमा १२ अक्षर): "),
    "password.mismatch": label(
        "The passwords are not the same. Nothing was changed.", "दुवै पासवर्ड मिलेनन्। केही पनि परिवर्तन गरिएन।"
    ),
    "password.short": label(
        "The password needs at least 12 characters. Nothing was changed.",
        "पासवर्डमा कम्तीमा १२ अक्षर चाहिन्छ। केही पनि परिवर्तन गरिएन।",
    ),
    "password.no_account": label(
        "There's no account for {email}. Nothing was changed.", "{email} को खाता छैन। केही पनि परिवर्तन गरिएन।"
    ),
    "password.done": label(
        "New password set for {email}, and it's signed out everywhere.",
        "{email} को नयाँ पासवर्ड राखियो, र यो सबै ठाउँबाट साइन आउट भयो।",
    ),
}

# Emails apply sends, in the account's language.
MAIL: dict[str, Label] = {
    "reset.subject": label("Reset your apply password", "तपाईंको apply पासवर्ड रिसेट गर्नुहोस्"),
    "reset.body": label(
        "Someone asked to reset the password for {email} on apply.\n\n"
        "To choose a new password, open this link:\n{url}\n\n"
        "It works once, for {minutes} minutes.\n\n"
        "If it wasn't you, ignore this email: your password stays the same.\n",
        "apply मा {email} को पासवर्ड रिसेट गर्न कसैले अनुरोध गर्नुभयो।\n\n"
        "नयाँ पासवर्ड छान्न यो लिङ्क खोल्नुहोस्:\n{url}\n\n"
        "यो एक पटक, {minutes} मिनेटसम्म मात्र चल्छ।\n\n"
        "यो तपाईं हुनुहुन्न भने यो इमेल बेवास्ता गर्नुहोस्: तपाईंको पासवर्ड जस्ताको तस्तै रहन्छ।\n",
    ),
}


def mail_text(key: str, locale: str, **values: object) -> str:
    entry = MAIL[key]
    return (entry.get(locale) or entry["en"]).format(**values)


def cli_locale() -> Locale:
    """The command line's language: APPLY_LANG, else the system's (LC_ALL, LANG), else English."""
    for name in ("APPLY_LANG", "LC_ALL", "LANG"):
        value = os.environ.get(name, "")
        if value:
            code = value.lower().replace("-", "_").split("_")[0].split(".")[0]
            return code if code in LOCALES else "en"  # type: ignore[return-value]
    return "en"


def t(key: str, locale: Locale | None = None, **values: object) -> str:
    entry = CLI[key]
    return (entry.get(locale or cli_locale()) or entry["en"]).format(**values)
