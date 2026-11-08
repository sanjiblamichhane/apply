<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/apply-logo-dark.svg">
    <img src="docs/brand/apply-logo.svg" alt="apply" height="72">
  </picture>
</p>

<h3 align="center">Your private job-search agent.</h3>

<p align="center">
  Finds roles, writes a tailored résumé and cover letter for each one, and fills in the application form.<br>
  It runs on your own machine with your own model, so your profile never leaves it. You always press Submit.
</p>

<p align="center">
  <a href="https://github.com/sanjiblamichhane/apply/actions/workflows/ci.yml"><img src="https://github.com/sanjiblamichhane/apply/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Licence: Apache-2.0"></a>
  <img src="https://img.shields.io/badge/runs-100%25%20local-07727d" alt="Runs 100% local">
  <a href="docs/mcp.md"><img src="https://img.shields.io/badge/MCP-server-07727d" alt="MCP server"></a>
  <img src="https://img.shields.io/badge/languages-English%20%C2%B7%20%E0%A4%A8%E0%A5%87%E0%A4%AA%E0%A4%BE%E0%A4%B2%E0%A5%80%20%C2%B7%20Espa%C3%B1ol-07727d" alt="English, Nepali, Spanish">
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="docs/getting-started.md">Guide</a> ·
  <a href="docs/mcp.md">Use it from an AI agent</a> ·
  <a href="docs/extension.md">Browser extension</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

![A short tour: paste a job, watch apply write the résumé and cover letter, and let the extension fill the form](demo/images/apply-tour.gif)

## Why apply

Job hunting is the same chores again and again: tailoring a résumé, writing a cover letter, and typing your
history into one more form. AI tools that do it for you usually want your whole career on their servers, and
some fire off applications in your name. apply takes a different line:

- **Private by design.** It runs on your computer with a local model (any server speaking the native
  `/api/chat` or the v1 `/v1/chat/completions` API). No account with us, no telemetry, nothing uploaded.
- **Honest documents.** Every résumé and cover letter is written only from your profile. A claim check flags
  anything it can't back up (an employer you never had, a number you never gave) before you send it.
- **Fills forms, never submits.** The browser extension shows what it will fill, fills it, attaches your
  PDFs, and lists what's left for you. You check it and press the form's own Submit button.
- **Works with your AI agent.** An [MCP server](docs/mcp.md) lets Claude, Cursor and other agents add jobs,
  read applications and fetch your profile, with a token that can never submit anything.
- **More than jobs.** Packs for jobs, public tenders, grants and contracts, each with its own profile,
  documents, pipeline and sources. In English, Nepali and Spanish.
- **Yours to change.** Apache-2.0, self-hosted with one compose file, and tested end to end.

## Quick start

You need Docker (or another container runtime with compose) and a local model server with a model downloaded.

```sh
git clone https://github.com/sanjiblamichhane/apply.git && cd apply
cp .env.example .env        # set POSTGRES_PASSWORD (long and random) and APPLY_LLM_MODEL
docker compose up -d        # database, API, worker and web app
```

Open <http://localhost:3310>, choose **Create your account**, and tick **Add a sample profile to look around**
(John Doe, made up) to explore before you add your own. Then load the [browser extension](#the-browser-extension).

The full guide is in [docs/](docs/README.md). To contribute, see [CONTRIBUTING.md](CONTRIBUTING.md); coding
agents should read [AGENTS.md](AGENTS.md). To report a vulnerability, see [SECURITY.md](SECURITY.md).

apply is an independent project. It isn't affiliated with, endorsed by or sponsored by any job board,
model server or other service it works with.

## See it

Everything below is the demo (John Doe, a made-up person, offered when you create your account) on a test model
server. The pictures and the demo's data are in [demo/](demo/).

**The applications board**, each one at its stage, with its documents:

![The applications board](demo/images/web-applications.png)

**One application**: its documents written from the profile, with a check that every claim is backed by it:

![An application and its résumé](demo/images/web-application.png)

**Settings → Model**: apply finds the model servers on this computer and tests a model before using it:

![Settings, Model](demo/images/web-model-settings.png)

**The browser extension filling a job's form.** First it shows what it would fill, and nothing is written until
you confirm:

![The extension's Fill preview beside an empty application form](demo/images/extension-fill-preview.png)

Then the form is filled and the documents attached. What's left (questions only you can answer) is listed, and
you check everything and press the form's own Submit:

![The form filled, and what's left listed in the panel](demo/images/extension-filled.png)

On any other site, **Copy** keeps your profile beside the form, a click from the clipboard:

<img src="demo/images/extension-copy.png" alt="The extension's Copy view: John Doe's details, ready to copy" width="320">

## What you need

- A container runtime with compose (for Postgres, and for the tests' throwaway databases)
- [uv](https://docs.astral.sh/uv/) (Python 3.12 is fetched for you)
- Node 22+ and pnpm 10 (for the web app)
- Pango, which prints documents to PDF: `brew install pango` (macOS), or
  `apt install libpango-1.0-0 libpangoft2-1.0-0` (Debian-based systems). The container image has it already.
- A local model server with a model downloaded, speaking the native API (`/api/chat`) or the v1 API
  (`/v1/chat/completions`); see [self-hosting](docs/self-hosting.md#the-model)

## Install in detail

With containers only (a local model server running on this machine):

```sh
cp .env.example .env                          # then set POSTGRES_PASSWORD and APPLY_LLM_MODEL in .env (never committed)
docker compose up -d                          # Postgres, file bucket, API, worker, web app on http://localhost:3310,
                                              # and a local mail catcher, where apply's emails land: http://127.0.0.1:8035
docker compose run --rm --name apply-init api apply init      # your owner account, once (or "Create your account" on first visit)
```

To look around first, without a model: `docker compose run --rm --name apply-demo api apply demo` makes a demo account with
something in every pack (on an empty database only).

From source, for development:

```sh
docker compose up -d postgres storage mail   # development Postgres on 127.0.0.1:54329 (password from .env),
                                         # the file bucket (a local storage emulator) on 127.0.0.1:4453, and the mail catcher
cd services/backend
echo "APPLY_DATABASE_URL=postgresql+asyncpg://apply:<POSTGRES_PASSWORD>@127.0.0.1:54329/apply" > .env
printf 'APPLY_SMTP_HOST=127.0.0.1\nAPPLY_SMTP_PORT=1035\nAPPLY_SMTP_SECURITY=none\n' >> .env   # email to the mail catcher
echo "APPLY_LLM_MODEL=<a model on your model server>" >> .env      # or choose one later in Settings → Model
uv sync
uv run apply migrate                   # create the tables
uv run apply init                      # your owner account (asks for a password)
uv run apply check-model               # does the model in use answer, and is it there?
uv run apply models                    # the model servers and models on this machine
uv run apply serve                     # the API on http://127.0.0.1:8110 (docs at /api/docs)
uv run apply worker                    # background work: reading postings, writing documents
```

Then the web app:

```sh
cd services/frontend
pnpm install
pnpm --filter @apply/web dev               # http://localhost:3310 (passes /api to 127.0.0.1:8110)
```

For model work on its own worker, one job at a time (a local model server answers one request at a time):
`apply worker --queue llm --concurrency 1`, plus `apply worker --queue default` for the rest.

Files (PDFs, screenshots, uploaded resumes) go to an object storage bucket, never the local disk: the
emulator above in development, a real bucket in the cloud (see [Running it yourself](docs/self-hosting.md#files)).

Settings come from `APPLY_*` environment variables or a `.env` file in `services/backend`; see
[settings.py](services/backend/src/apply/settings.py). The command line speaks Nepali or Spanish with `APPLY_LANG=ne` or `es` (or your system's language).

## Using it

Every page, and each part of one, has a **?** that opens its guide beside it, in English, Nepali or Spanish (the guides
are Markdown in `services/frontend/apps/web/src/help/guides`).

The sidebar's **Working on** switch picks the pack: Jobs, Tenders, Grants or Contracts (remembered on this
device). Applications, Profiles, Matches, Searches, Sources and Saved answers then show and create that
pack's own; Today covers them all. Each pack brings its profile and notice fields, its documents (resume and
cover letter; capability statement and tender response; letter of inquiry and project narrative; proposal and
statement of work), its pipeline and its sources. The sidebar collapses to icons with the button beside the
name, and stays in place while the page scrolls.

1. **Profiles**: who is applying. Every document is written from the profile, and nothing else gets claimed.
2. **Applications**: paste a link or a posting's text. apply reads it and puts it on the board.
3. **Sources and searches** (optional): public listings are fetched on a schedule: companies' own job
   boards (paste a board's address and apply recognises it), UK public tenders (Contracts Finder, under the Open Government Licence) and US
   federal grants (Grants.gov). Contracts have no public source: paste each brief. Postings that fit a saved search are scored against your profile and land in **Matches**, and
   **Today** sums up what's new each morning.
4. **Documents**: a resume and cover letter written for each application by your model. A claim check flags
   anything your profile doesn't back up (an invented employer, a number you never gave). You fix each
   warning or say "It's true", then mark the version as reviewed. **Preview** shows a version in your
   template, as it will be downloaded, then as a tagged PDF (the page printed) or the page itself (HTML).
   Each document is made in your template (one for resumes, one for letters). A default comes for each,
   and you can download it, change its HTML and CSS, and upload it in **Settings → Document templates**.
   It's used only once it's safe and passes WCAG 2.2 AA checks.
5. **Saved answers**: answers to the questions forms keep asking. Equal-opportunity questions are sensitive.
   They start as "Decline to answer" and are never sent to a model.
6. **Application kit**: on each application, the steps to apply anywhere by hand: open the form, download
   the PDFs, copy your answers, then "I've submitted it". That records what went out and moves the
   application along. You can undo it for 10 minutes.
7. **Browser extension**: beside any page, your profile in tabs; click a value to copy it and paste it
   into any form. And on the forms of the supported job boards (listed by address in `boards.json`), and on
   any site you allow, it shows what it would fill, then fills in your profile,
   attaches your PDFs and puts in your saved answers. Anything it isn't sure of is left blank and listed for you.
   You check the form and press its Submit button yourself; apply never does. When the board says thank
   you, the extension records the submission and moves the application along, with Undo.

8. **Auto** (off unless you turn it on, per search): strong matches are tracked, and their resume and
   cover letter written and checked (any claim warning sends one to **Needs you**). They then wait in **Ready
   for you**: open each one, let the extension fill it, and press Submit yourself. **apply never submits an
   application**: no board offers a candidate a sanctioned way to, and their terms forbid automated access
   ([docs/auto.md](docs/auto.md)). **Pause Auto** stops everything at once. The limits (a fit of 80, 5 a day,
   nothing to the same employer within 30 days) are in Settings → Auto.

## The browser extension

```sh
cd services/frontend && pnpm --filter @apply/extension build    # → services/frontend/apps/extension/dist
```

In your browser, open its extensions page (`chrome://extensions`), turn on Developer mode, choose **Load unpacked** and pick
`services/frontend/apps/extension/dist`. Then, in apply, go to **Settings → Browser extension** and make a
token. Open the extension's side panel (its toolbar button) and paste the token in.

The extension may reach only the supported job boards and apply on this computer (`127.0.0.1:8110`). Your
browser asks before it reaches any other address you give it. Its token can only read your applications, track new jobs
and record submissions. It can't change your profile or make more tokens, and you can revoke it in Settings
at any time.

## Tests

Every check is a test or a script:

```sh
tests/check.sh          # everything below the real model: backend lint and suites, the web app's lint,
                        # typecheck, unit tests (i18n, contrast, kit, api, ats-adapters, extension, web) and browser
                        # journeys (Playwright and axe: the web app, and the extension in a test browser)
tests/check.sh fast     # the same without the browser journeys
tests/live.sh           # the journeys against your real model server, with timings, and the form adapters on one
                        # real public form per board (read only: nothing is typed or sent);
                        # APPLY_LIVE_SOURCES=1 also reads every real source once (boards, Contracts Finder,
                        # Grants.gov)
tests/docker-smoke.sh   # the container images: build, migrate, sign in through the web app, a file to the bucket
```

Contrast of every colour token, light and dark, is in
[services/frontend/packages/ui/CONTRAST.md](services/frontend/packages/ui/CONTRAST.md).

Backups: `apply export --out backup.json`, `apply import backup.json`.

The tests never touch your development database. Each run starts its own throwaway Postgres and bucket
(compose.test.yml, one named project per suite, removed after), applies the real migrations, and ignores
`APPLY_*` variables and `.env`.

## Exposing apply

apply binds to `127.0.0.1` and refuses any other address unless you set `APPLY_ALLOW_REMOTE=1`. Before
you do, know what it means: anyone who can reach the port can try to sign in, and your profile and
documents are behind that one password. Put it behind HTTPS (cookies become `Secure` and `__Host-` scoped
automatically off localhost) and set `APPLY_ALLOWED_ORIGINS` to the web app's address.

## Layout

```
services/backend/      FastAPI (uv): api/ (routes, schemas), logic/, store/sql/ (models, queries,
                       migrations), packs/ (job, tender, grant, contract, common
                       prompts), libs/ (llm, jobs, extract), tests/
services/frontend/     Turborepo: apps/web (Next.js), apps/extension (browser extension, MV3),
                       packages/ (ui, kit, i18n, api, ats-adapters: reading and filling board forms,
                       e2e-harness: the journeys' stack)
docs/                  the guide
tests/                 check.sh, live.sh, docker-smoke.sh
```

## Author

apply is written and maintained by [@sanjiblamichhane](https://github.com/sanjiblamichhane), its copyright
holder and code owner. Copyright 2026 sanjiblamichhane, under the Apache License 2.0 (see [LICENSE](LICENSE) and
[NOTICE](NOTICE)). Changes are listed in [CHANGELOG.md](CHANGELOG.md).
