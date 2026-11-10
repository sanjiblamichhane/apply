# Changelog

All notable changes to apply. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-08

The first public release.

### Added

**Applying**

- **Packs:** jobs, public tenders, grants and freelance contracts, each with its own profile, opportunity
  details, documents, pipeline and saved questions. Screens are drawn from each pack's schema.
- **Applications:** paste a link or a posting's text, or track a match. A board and a list, each application's
  pipeline and history, and follow-ups. The application opens beside the board, as the wider side, each side
  scrolling on its own, with its parts in tabs (documents, the kit, the details, notes and history). **Delete**
  removes one with its documents and history (its posting stays), with **Undo** instead of a
  confirmation.
- **Documents:** résumés, cover letters and each pack's own, written by your local model from your profile only.
  A claim check flags anything the profile doesn't back up (an invented employer, a number you never gave); fix
  it, say "It's true", or say "It's wrong" and what's true instead; each warning shows the sentence it's in.
  **Write it again with your changes** has your model write a new version from your corrections and notes, and
  the check counts your corrections as your own facts. Then mark the version reviewed. Edit, keep versions,
  and preview each one as it will be downloaded: a tagged PDF/UA-1 in apply's own fonts, or the page itself
  (.html). Or download it as Word (.docx) to edit: the same headings, in Word's own styles.
- **Document templates:** every document is made in your template, an HTML page with placeholders: one for
  résumés and documents in sections, one for letters. **Settings → Document templates** previews, downloads and
  uploads them. An upload is used only if it's safe (no scripts, nothing fetched) and, filled with a sample,
  passes WCAG 2.2 AA checks; each problem is named with its success criterion. Paper defaults to US Letter;
  set `APPLY_PDF_PAPER=a4` or `@page` in a template.
- **Profiles:** fill one in by hand or upload a résumé (PDF, .docx or text) and your model fills it in, in any
  pack; only what the document says is kept, and you check every field. A job's start or end given only as a
  month gets a day (the 15th to start, the 30th to end, February's last day), since forms ask for one; résumés
  and letters still show the month. An address (line by line, with the phone's country code) for forms that ask.
  **Duplicate** a profile to change it for other roles.
- **Saved answers** to the questions forms keep asking. Equal-opportunity questions start as "Decline to
  answer" and are never sent to a model.
- **Application kit:** the steps to apply anywhere by hand (open the form, download the PDFs, copy your
  answers), then "I've submitted it", with 10 minutes to undo.

**Finding opportunities**

- **Sources:** companies' own job boards and careers sites, UK public tenders and US federal grants, each from
  the platform's own public API or feed, as often as its terms allow, and credited where they ask. Paste a
  board's address (or one of its jobs) in **Sources → Add a source** and apply recognises it.
- **Searches and matches:** postings that fit a saved search are scored against your profile and land in
  **Matches**; **Today** sums up what's new each morning.
- **Auto** (off unless you turn it on, per search): strong matches are tracked and their documents written and
  checked, then wait in **Ready for you** (or **Needs you**, after a claim warning). **apply never submits an
  application**: you open each one, let the extension fill it, and press Submit yourself
  ([docs/auto.md](docs/auto.md)). **Pause Auto** stops everything at once; its limits are in Settings → Auto.

**The browser extension** (MV3)

- **Fill:** on the supported job boards, and on any site you allow with **Use apply on this site**, it lists each
  field with the value it would put there, the files it would attach and what's left for you, and waits. Untick
  anything you'd rather type, then press **Fill the form**. It fills by the labels (forms inside web components
  too), attaches your PDFs and puts in your saved answers. For a board's own dropdowns it shows your answer and
  you choose it. **Check the form again** reads the form afresh. When the board says thank you, it records the
  submission and moves the application along, with Undo.
- **Copy, on any site:** your profile in tabs (Basics, Experience, Education, More, Answers) with one search.
  Click a value to copy it: names in parts, the address line by line, dates in the forms forms ask for.
  Equal-opportunity answers stay hidden until you show them, and **Clear the clipboard a minute after copying**
  is an option.
- A compact panel with every tool named in a tooltip, a link that opens apply in a new tab, a profile picker with its own search, and its own
  Settings (language, clipboard, theme, Disconnect).
- **Tokens:** the extension acts with a personal token made in Settings, which can only read your applications
  and profile, track new jobs and record submissions; revoke it at any time.

**AI agents**

- **An MCP server:** `apply mcp` lets Claude Desktop, Claude Code, Cursor and other MCP clients track postings,
  read applications, your profile and saved answers, and ask for draft documents ([docs/mcp.md](docs/mcp.md)).
  Make its token with **An AI agent** in **Settings → Extension and AI agents** (or `apply token --kind agent`).
  It can never record a submission.
- `AGENTS.md` and `llms.txt` describe the project for coding agents and AI tools.

**Running it**

- **Your own machine, your own model:** compose runs Postgres, a file bucket (a local storage emulator), the API,
  the worker, the web app and a local mail catcher, all bound to 127.0.0.1 with every secret in `.env`. Files
  (PDFs, screenshots, uploaded résumés) go to an object storage bucket, a real one in the cloud.
- **Settings → Model** finds the models on this computer's local model servers (any server speaking the native
  `/api/chat` or the v1 `/v1/chat/completions` API), shows each one's size and context, and tests a model before
  using it. The choice takes effect at once; `apply models` lists them from the command line.
- **Accounts:** the first account is the owner's; after it, anyone who can reach apply can make their own and
  sees only their own work. **Settings → People** lets the owner close registration, see who has an account,
  turn one off or delete it. **Forgot your password?** emails a one-time link (or use `apply password`).
- **A demo:** tick **Add a sample profile to look around** when you create your account to get John Doe, a made-up
  person, with applications, documents, a search and its matches. `apply demo` makes a demo account from the
  command line. The data, the README's screenshots and the tour are in demo/.
- **Your data:** `apply export` and `apply import` round-trip everything you made.

**For everyone**

- **Languages:** English, Nepali and Spanish, for every screen, guide, server label and the command line. The
  Nepali and Spanish are first drafts for native speakers to review.
- **Help:** a guide for every page and part of a page, in each language, docked beside the page on wide screens.
- **Accessibility:** WCAG 2.2 AA, 44 px targets, light and dark themes, an automated contrast test of every
  colour pair (packages/ui/CONTRAST.md) and axe on every screen in the browser journeys.
- **A palette and a logo:** cyan as the primary colour, red for errors, green for success, orange for secondary
  buttons; a cyan tile holding an "a" with a dot lifting off it, then the word "apply". The files are in
  docs/brand.
- **Adding a platform or a pack:** one list of boards (`boards.json`), a recording per source held to the same
  checks, and `tools/new-platform.py` for the stubs (CONTRIBUTING.md).

### Security

- An independent review before release; every finding is fixed with a test, or accepted with the reason
  written down.
- Personal tokens are stored only as hashes, carry scopes, expire and can be revoked at once. apply refuses any
  address but 127.0.0.1 unless `APPLY_ALLOW_REMOTE=1`.

[Unreleased]: https://github.com/sanjiblamichhane/apply/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sanjiblamichhane/apply/releases/tag/v0.1.0
