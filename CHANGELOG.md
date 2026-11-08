# Changelog

All notable changes to apply. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **A demo when you create your account:** tick **Add a sample profile to look around** to get John Doe, a
  made-up person, with three applications, their documents, a search and its matches, in lorem ipsum. It's off
  unless you tick it. The data and the README's screenshots are in demo/.
- **A new palette:** red #ED1F2F, cyan #0DC8DB, green #52D932, yellow #FFC729 and orange #FF8008. Cyan is the
  primary colour, red marks errors, green success, orange secondary buttons, and a yellow tint highlights menu
  items. Dark mode uses them as they are; light mode uses deeper shades of the same hues for text and buttons,
  so every pair still passes WCAG 2.2 AA (packages/ui/CONTRAST.md). The logo and icons follow.
- **Ready to release as open source:** no third-party company or product names in the screens, guides, docs
  or code.
  - **Sources come from an address:** in **Sources → Add a source**, paste a company's job board address (or
    one of its jobs) and apply recognises the board and fills in what it needs. The screens no longer list
    platforms by name, and the extension speaks of "supported job boards" and "this site".
  - **The aggregator job feeds are removed.** Sources you saved from them are gone; the postings they found
    stay. Companies' own job boards and the public-sector feeds remain.
  - **Model servers are known by the API they speak**, the native API (`/api/chat`) or the v1 API
    (`/v1/chat/completions`), not by product. Settings → Model shows each server by its address.
    `APPLY_LLM_API` is now `native` or `v1`, and `APPLY_LLM_DISCOVER_PORTS` is a list of ports. A model chosen
    before this change is cleared: choose it again.
  - **No default model:** set `APPLY_LLM_MODEL` in `.env`, or choose one in Settings → Model.
  - **The mail catcher's compose service is now `mail`** (container `apply-mail`, volume `apply_mail`). The old
    volume can be deleted.
  - The README and NOTICE say apply is independent and not affiliated with any service it works with.
- **A logo:** a cyan rounded tile holding an "a" with a dot lifting off it, then the word "apply" in monoline
  letters; the tile alone is the icon. It shows in the sidebar, on the sign-in pages, in the browser tab, on the
  extension's connect screen and in the browser's toolbar. The files for slides and print are in docs/brand.
- **Copy from the extension, on any site:** the extension's panel shows your profile in tabs (Basics, Experience,
  Education, More, Answers) with one search. Click a value to copy it, then paste it into the form. Names come in
  parts, the address line by line, and dates as 01/2021 and 2021-01 too. Equal-opportunity answers stay hidden
  until you show them. It never touches the page. **Clear the clipboard a minute after copying** is an option.
  Filling forms is now the panel's **Fill** view. The token needs the new "Read your profiles" permission:
  make a new one and connect again.
- **A compact copy panel:** one row at the top holds the profile and every tool (search, refresh, Copy as a
  clipboard, Fill as a magic wand, Settings), each icon named in a tooltip on hover or keyboard focus. The profile
  is a dropdown with its own search, so it works the same for two profiles or fifty. The section tabs wrap instead
  of hiding, the values add columns as the panel widens, and each job folds to one line, with each of its fields
  once (no "All of it" tile repeating the whole job). Type and press Enter to copy the first match. The language,
  the clipboard setting and Disconnect moved to the panel's Settings, which can also set the theme (Match the
  system, Light or Dark). The extension is now 0.2.0.
- **Fill shows what it will fill, and waits for you:** before anything goes into the form, the extension's Fill
  view lists each field with the value it would put there, the files it would attach, what's left for you and
  why, and what's already filled (it stays). Equal-opportunity answers are hidden until you show them. Untick
  anything you'd rather fill yourself, then press **Fill the form**: only the ticked fields are filled, and the
  unticked ones are listed as yours. **Check the form again** (↻ at the top of Fill) reads the form afresh,
  fetches your latest profile and answers, and matches again.
- **An address in your profile:** line 1, line 2, city, state or region, postcode and country, plus your phone's
  country code. They're copied, filled into forms that ask for them (a board's "My Information" step), and the city and
  region stand in for "Where you live" when that's empty.
- **Forgot your password?** on the sign-in page emails a link to choose a new one. The link works once, for 30
  minutes, and a new password signs that account out everywhere. The answer is the same whether or not there's
  an account with that email. Compose runs a **local mail catcher**, so the email stays on this machine
  (<http://127.0.0.1:8035>); set `APPLY_SMTP_*` to send real email. Without email, `apply password` sets a
  new password from the command line.
- **Accounts for everyone:** after the owner's first account, anyone can make their own with **Create an
  account** on the sign-in page, and sees only their own work. **Settings → People** is for the owner: close
  registration, see who has an account, turn one off or on, or delete one. Only the owner chooses the shared
  model, and at most 5 accounts can be made from one address an hour.
- **Delete an application:** **Delete** on its page removes it with its documents and history, while its posting
  stays. **Undo** is offered for a few seconds instead of a confirmation. An Auto run on it stops, and a
  match that tracked it goes back to saved. Beside the board, ✕ closes the application.
- **A board's own dropdowns show your answer:** for "Select One" lists and a "How did you hear about us?"
  search, the extension shows the answer from your saved answers, and you choose it. "Have you ever been employed
  by …?" shows Yes when your profile's work history has that employer. The extension never opens, types into or
  clicks a board's own dropdowns.
- **Document templates:** every resume and cover letter is made in your template, an HTML page with
  placeholders. There's one for resumes (and other documents in sections) and one for letters. The defaults
  are the given resume and cover-letter pages. **Settings → Document templates** lets you preview,
  download and upload your own. An upload is used only if it's safe (no scripts, nothing fetched) and,
  filled with a sample, passes WCAG 2.2 AA checks. Each problem is named with its success criterion.
  Your name and contact line come from your profile, and a letter's date is added for you.
- **Preview before download:** each version opens as it will be downloaded. **Download PDF** prints that
  same page to a tagged PDF/UA-1, in apply's own fonts on every machine. You can also download the page
  itself (.html).
- **Settings → Model** finds the models on this computer's local model servers. It shows each model's size, parameters, context, and whether it's loaded.
  Choose a model and a writing model. apply tests a model before using it, and the choice takes effect at
  once, with no restart. `apply models` lists them from the command line.
- **A profile from your resume:** upload a PDF, .docx file or text, and your model fills in the profile from it,
  in any pack. Only what the document says is kept; you check every field. Edits made while it reads win.
- **Duplicate a profile** to change what's different for other roles.
- **Guides dock beside the page** on wide screens, and the page narrows to make room. On narrower screens the
  guide is a sheet, now 24 rem wide.
- **An application beside the board:** each side scrolls on its own, and the page stays still.
- **More sources:** more companies' job boards and careers sites, each from the platform's own public API or
  feed, as often as its terms allow, and credited where they ask.
- **The extension fills more forms:** on more supported job boards, by their labels. On any other site,
  **Use apply on this site** asks the browser for that one site. Forms drawn inside web components are read
  too.
- **Adding a platform:** one list of boards (`boards.json`), a recording per source held to the same checks,
  and `tools/new-platform.py` for the stubs (CONTRIBUTING.md).

### Changed

- **Auto prepares, and you send.** apply no longer submits applications. Strong matches from a search with
  Auto on are tracked and their documents written and checked. They then wait in **Ready for you**: open one,
  let the extension fill it, and press Submit yourself. No board offers a candidate a sanctioned way to submit
  automatically: their submission APIs need the employer's key, and their terms forbid automated access
  ([docs/auto.md](docs/auto.md)). Runs that were waiting to be sent are now Ready for you. One that was
  being sent is in Needs you, because it may have gone. Past runs keep their screenshots and submissions.
- **Files are kept in an object storage bucket**, not the database: PDFs, Auto's screenshots and uploaded
  resumes. Compose runs a local storage emulator; in the cloud, point apply at a real bucket. Files already in the database
  move to the bucket on the first start. `/api/v1/health` reports the bucket too.
- **PDFs are printed from the document's page**, replacing the separate layout engine. Printing needs Pango;
  the container image has it, and the README says how to install it elsewhere. Paper
  defaults to US Letter, the templates' width. Set `APPLY_PDF_PAPER=a4` for A4, or set `@page` in a template.
- The writing prompts follow the template: a resume's sections are in its order with its headings, and a
  letter starts at "Dear …".

### Removed

- A one-off importer for a private project, and reading backups made under the product's earlier name.
- **Auto's runner** (`apps/runner`, `docker compose --profile auto`), runner tokens (revoked on upgrade), and the
  hold before sending. Drafting free-text answers is gone too, since it needed the runner to read the form
  first. `APPLIED_RUNNER_TOKEN` in `.env` is no longer read.
- The opt-in live check that opened real boards' forms in a scripted browser. The live suite now uses only
  their public APIs.

## 0.1.0 - 2026-10-27

The first public release.

### Added

- **Packs:** jobs, public tenders, grants and freelance contracts, each with its own profile, opportunity
  details, documents, pipeline and saved questions. Screens are drawn from each pack's schema.
- **Applications:** paste a link or text, or track a match. A board and a list, each application's pipeline
  and history, and follow-ups.
- **Documents:** CVs, cover letters and each pack's own, written by your local model from your profile only. A claim check flags anything the profile doesn't support. Edit, keep
  versions, and download tagged PDF/UA-1.
- **Discovery:** sources (public job boards' APIs and feeds, within their terms and rate limits), saved
  searches, matches scored against your profile, and a daily briefing.
- **Auto:** a runner that fills and sends applications within your rules. It's off by default, holds every run
  for review first, can be paused, never ticks a consent box, and never answers a sensitive question.
- **Browser extension** (MV3): fills a board's form from your profile and saved answers, then you check
  it and press Submit.
- **Languages:** English, Nepali and Spanish, for every screen, guide, server label and the command line. The
  Nepali and Spanish are first drafts for native speakers to review.
- **Help:** a guide for every page and part of a page, in each language.
- **Your data:** `apply export` and `apply import` round-trip everything you made; `apply demo` gives you
  a demo account to look around without a model.
- **Running it:** compose (Postgres, API, worker, web, and the runner behind a profile), all bound to
  127.0.0.1, with every secret in `.env`.
- **Accessibility:** WCAG 2.2 AA, with an automated contrast test and axe on every screen, in light and dark.

### Security

- An independent review before release; every finding is fixed with a test, or accepted with the reason
  written down.

[Unreleased]: https://github.com/sanjiblamichhane/apply/commits/main
