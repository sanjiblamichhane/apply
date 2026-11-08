# Contributing to apply

Thank you for helping. apply writes documents people send to employers, buyers and funders, so we're
careful: nothing it writes may claim what the person's profile doesn't say, nothing it does may get around a
site's defences, and everything a person sees must work in English, Nepali and Spanish, for everyone.

apply is maintained by [@sanjiblamichhane](https://github.com/sanjiblamichhane), who reviews every pull request
(see [CODEOWNERS](.github/CODEOWNERS)).

## Setting up

Follow **Install in detail** in the [README](README.md#install-in-detail): Postgres in a container, the backend with `uv`, the web app with `pnpm`.
For the model, run any local model server with a model downloaded. The tests don't need it; they use a fake one.

## The ground rules

1. **Every check is a test or a script.** If you checked something by hand, turn it into a test before you open
   the pull request. `tests/check.sh` must pass, and `tests/check.sh fast` gives quicker feedback while you work.
2. **Tests never touch real data.** Each run starts a throwaway Postgres and bucket from `compose.test.yml`, as
   a named project, and removes them after. Never `docker run` or anything unnamed: every container, image and
   volume comes from a compose file and has a name. Real third-party sites are only read in the opt-in live
   suite (`tests/live.sh`), never in `check.sh`.
3. **Nothing invented.** Prompts write from the PROFILE only and mark anything missing as
   `[CONFIRM: …]`. The claim check runs on everything written. A change that makes it easier for a model to
   embellish won't be merged.
4. **Never get around a defence, and never act for the person on a site.** No solving CAPTCHAs, no ticking
   consent boxes, no pressing Submit, no scripted browser on a board's site: the person submits, in their own
   browser. Respect each source's terms and rate limits (`min_interval_hours`), and use only official public
   APIs and feeds.
5. **English, Nepali and Spanish for every string.** Write English and Nepali next to each other in
   `services/frontend/packages/i18n/src/messages`, and Spanish in `src/locales/es.json`; the i18n tests check
   that each message exists in every language, with the same placeholders. Pack labels (`labelled()`) take
   English and Nepali inline, with Spanish in `services/backend/src/apply/locales/es.json`, keyed by the
   English. Nepali and Spanish are first drafts: corrections from native speakers are very welcome.
   Adding a language is one catalogue in each place, its guides, and a line in each language list (the tests
   say what's missing).
6. **Accessibility is the bar, not a bonus.** WCAG 2.2 AA, clear and consistent layout and
   behaviour, and 44 px targets. If you change a colour, run the contrast test (`packages/ui`), add any new
   pair to it, and put the light and dark ratios in the pull request. Nothing may be conveyed by colour alone.
   The Playwright journeys run axe on every screen, in light and dark.
7. **Every page and part of a page has a guide.** Each guide is a folder, `apps/web/src/help/guides/<slug>/`, with
   one file per language (`en.md`, `ne.md`, `es.md`) that starts with a `title:` front matter. Link to another guide
   with a relative link to its folder (`[Searches](../searches/)`). Each **?** (`<Help slug="…" />`) names a guide.
   A test checks every guide is in every language with a title and working links, every **?** has a guide, and
   each **bold** label in a guide is written exactly as the screens show it.
8. **Fonts and icons:** Inter, and the Apache-2.0 icon set in `packages/ui/src/icons.ts`. Only openly licensed
   fonts and icons: never ones whose licences restrict them to one vendor's platforms.

## Code layout and conventions

- **Backend** (`services/backend`): FastAPI and async SQLAlchemy.
  - `api/` holds routes and schemas, `logic/` the rules, `store/sql/` the models and queries (with
    Alembic migrations), `libs/` the parts that know nothing of apply (llm, jobs, extract), and `packs/`
    the packs.
  - Errors are RFC 9457 problems with a stable `ErrorCode`; the web app translates each code.
  - Every table has an `owner_id`, and every query filters on it.
  - Tools: `uv`, `ruff` and `pytest`.
- **Web and clients** (`services/frontend`): a Turborepo.
  - `apps/web` is Next.js; `apps/extension` the browser extension.
  - `packages/ui` holds the components, `packages/kit` the screens' building blocks, `packages/i18n` the
    strings, `packages/api` the generated client, and `packages/ats-adapters` reads and fills board forms.
- When the API changes, run `uv run apply openapi --out openapi.json` in `services/backend`, then
  `pnpm --filter @apply/api generate`.

## Adding a pack

A pack is a module under `services/backend/src/apply/packs/`. The engine names no pack; a test checks this.

- Most packs subclass `DeclarativePack` (`packs/simple.py`). A pack declares:
  - its profile and opportunity models, with `labelled()` (`L`) on every field, in English and Nepali (Spanish in
    `locales/es.json`);
  - its document types, with their prompts;
  - its pipeline and its standard questions;
  - optionally, its sources.
- Prompts it doesn't define (score, extract, claims, answers) come from `packs/common/prompts`.
- Register it in `packs/__init__.py` (`BUILT_IN`).
- The web app draws its forms from the schema. Add pack-specific wording only where the generic text reads
  badly: a key such as `applications.paste.label.<pack>` in `packages/i18n`.
- Tests: copy `tests/unit/test_more_packs.py` and `tests/api/test_more_packs.py` for your pack. A source
  needs a recorded answer in `tests/support/boards.py` and an entry in the live suite.

## Adding a platform

A platform can be supported in two ways, separately or both. `tools/new-platform.py` writes the stubs and prints
what's left to add.

**A source** (listings, on a schedule), only from an API or feed the platform publishes for others to read,
within its terms: no scraping, no signing in, no getting round limits. A site without such an API isn't a source.

1. `tools/new-platform.py source <key> --name "<Name>" --url "https://{company}.example.com"` writes
   `packs/job/sources/<key>.py`.
2. Ask the platform's API once by hand, and finish `fetch()` from what it really answers. Keep to its terms:
   `min_interval_hours`, and `attribution` (shown as "via …") when its terms ask to be named. Give it
   `addresses`, the patterns of its board pages, so a pasted address is recognised (Sources → Add a source).
3. Register it in `sources/__init__.py`, and add its recording to `tests/support/recordings.py`: the answer's
   shape as the platform gave it, with made-up postings.
4. Keep labels neutral ("Company job board"): the UI never names a platform. Write each label's Nepali in the source and its Spanish in `locales/es.json`.
5. `uv run pytest tests/unit/test_every_source.py tests/unit/test_i18n.py`. Every source is held to the same rules
   there: it reads its recording over HTTP and never anything else, makes https links, unique refs and fields the
   pack takes, asks at most hourly, and says who to credit. A source without a recording fails.

**A board** (the extension fills its forms):

1. `tools/new-platform.py board <key> --name "<Name>" --host "*.example.com"` adds it to
   `packages/ats-adapters/src/boards.json`, the one list the registry and the extension's manifest come from.
2. Add its `defineBoard` line to `adapters/more.ts` (most need only the path of their form: the biggest form on
   the page is read by the label rules), and one of its form addresses to `tests/boards.test.ts`.
3. Where a board's form is unusual, record it in `fixtures/boards.ts` and fill it in a test the way
   `tests/adapters.test.ts` does board01's. Never press anything inside a board's own widgets: read them,
   and leave the choice to the person (as board04's dropdowns are).

Any other site already works without a board: the extension's **Use apply on this site** asks the browser
for that one site and fills its biggest form by the labels.

## Pull requests

Keep each one to a single change, say what it changes and how it was tested, and include before and after
screenshots for anything people see. By contributing, you agree that your contribution is licensed under
Apache-2.0, the project's licence.
