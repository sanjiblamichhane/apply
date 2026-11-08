# AGENTS.md

How to work on apply as a coding agent. People: [CONTRIBUTING.md](CONTRIBUTING.md) says the same at more length.

## What apply is

A self-hosted workspace for anything a person applies for (jobs, tenders, grants, contracts). It finds or takes
pasted opportunities, scores them against the person's profile, writes tailored documents with the person's
own local model, helps fill the application form through a browser extension, and tracks each application.
It runs on the person's machine; their data never leaves it.

## Layout

```
services/backend/    Python 3.12, FastAPI, async SQLAlchemy, Alembic, uv
  src/apply/api/       routes and schemas (RFC 9457 errors with a stable ErrorCode)
  src/apply/logic/     the rules
  src/apply/store/sql/ models, queries, migrations (every table has owner_id; every query filters on it)
  src/apply/packs/     job, tender, grant, contract: profile and opportunity models, documents, prompts, sources
  src/apply/libs/      parts that know nothing of apply: llm, jobs, extract, render
  src/apply/mcp_server.py the MCP server (`apply mcp`)
  tests/unit, tests/db, tests/api
services/frontend/   pnpm and Turborepo
  apps/web             Next.js app (port 3310)
  apps/extension       browser extension (MV3)
  packages/ui          components (shadcn/ui based) and theme tokens, with a contrast test
  packages/kit         screens' building blocks
  packages/i18n        every string, in English, Nepali and Spanish
  packages/api         client generated from services/backend/openapi.json
  packages/ats-adapters reading and filling board forms
docs/                the user guide
tests/               check.sh (everything), docker-smoke.sh (images), live.sh (real model, opt-in)
```

## Commands

```sh
tests/check.sh fast                       # lint, types, unit and API suites: run before you say you're done
tests/check.sh                            # also the Playwright journeys (web and extension, axe on every screen)
cd services/backend && uv run pytest tests/unit -q      # quick backend loop
cd services/backend && uv run ruff format && uv run ruff check src tests
cd services/frontend && pnpm turbo run typecheck test   # quick frontend loop
```

After changing the API: `cd services/backend && uv run apply openapi --out openapi.json`, then
`cd services/frontend && pnpm --filter @apply/api generate`. check.sh fails while openapi.json is stale.

## Rules that block a merge

1. **apply never submits an application,** and nothing may press Submit, solve a CAPTCHA, tick consent boxes or
   script a browser on a job board. The person submits in their own browser. Sources use only official public
   APIs and feeds, within their terms and rate limits.
2. **Nothing invented.** Documents are written from the profile only; missing facts become `[CONFIRM: …]`, and
   the claim check runs on everything written.
3. **Tests never touch real data.** Every suite starts throwaway Postgres and storage from `compose.test.yml` as
   a named compose project. Never `docker run`, and never an unnamed container, image or volume. Tests use a
   fake model server; no test reaches a third-party site (only `tests/live.sh`, opt-in).
4. **Every string in English, Nepali and Spanish.** English and Nepali side by side in
   `services/frontend/packages/i18n/src/messages`, Spanish in its `src/locales/es.json`; backend pack labels
   with `labelled()` and `services/backend/src/apply/locales/es.json`. The i18n tests say what's missing.
5. **Accessibility: WCAG 2.2 AA,** 44 px targets, nothing conveyed by colour alone. Changing a colour means
   running the contrast test in `packages/ui` and adding any new pair to it.
6. **Every page and part of a page has a guide** in `apps/web/src/help/guides/<slug>/{en,ne,es}.md`.
7. **Every check is a test or a script.** If you verified something by hand, add the test.
8. Only openly licensed fonts and icons (Inter; the icon set in `packages/ui/src/icons.ts`).

## Style

Plain, short sentences in code comments, docs and UI text. Docstrings say what a thing is for, not how it
works line by line. Keep changes small and in the existing patterns; read the neighbouring code first.
