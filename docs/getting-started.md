# Getting started

apply runs on your own computer, with your own model. Your profile and documents never leave it.

## What you need

- A container runtime with compose.
- A local model server with a model downloaded, speaking the native API (`/api/chat`) or the v1 API
  (`/v1/chat/completions`). Choose the model in **Settings → Model**, or name it in `.env` as `APPLY_LLM_MODEL`;
  it never leaves your computer.

## Install and make your account

```sh
cp .env.example .env                          # then set POSTGRES_PASSWORD in .env (a long random one) and APPLY_LLM_MODEL
docker compose up -d                          # the database, the API, the worker and the web app
docker compose run --rm --name apply-init api apply init      # your account (asks for an email and a password, 12+ characters)
```

Open <http://localhost:3310>. On the first visit you can make the account there instead, with **Create your
account**. The first account is the owner's. Set `APPLY_WEB_SETUP=0` to allow `apply init` only, for an
install others can reach before you've set it up.

### More people

After the first account, anyone who reaches apply can make their own with **Create an account** on the
sign-in page. Each account sees only its own profiles, applications, documents, templates and settings. The
model is shared, and only the owner chooses it.

The owner runs this in **Settings → People**:

- close registration, so no new accounts can be made;
- see who has an account and when they last signed in, but never what's in it;
- turn an account off, which signs it out and stops its sources and Auto; turning it on again restores it;
- delete an account with everything in it.

**Forgot your password?** on the sign-in page emails a link to choose a new one. With compose, the email lands in
a local mail catcher at <http://127.0.0.1:8035>, on this machine; [Running it yourself](self-hosting.md#email) says how to
send real email.

From one address, at most 5 accounts can be made an hour. If apply can be reached from the internet, close
registration once everyone who should have an account has one. The sign-in pages are always in English; choose Nepali or
Spanish in Settings once you're in.

## Or look around first

The demo makes an account that already has something in every pack: profiles, applications with their
documents written, a search with scored matches, and saved answers. It needs no model, and Auto is paused in it.

```sh
docker compose run --rm --name apply-demo api apply demo      # demo@example.com, with a password you choose
```

It only runs on a database with no accounts. Use a fresh one, or `--force --email you@example.com` to add the
demo to your own account on purpose.

## The first ten minutes

1. **Profiles → New profile.** Who's applying, and the facts you'd stand behind. Every document is written
   from these, and nothing else gets claimed. Quickest: **Choose a file** and upload your resume; your model
   fills in the profile from it, and you check every field. **Duplicate** makes a second profile to change
   for other kinds of roles.
2. **Applications.** Paste a link to a job, or its text. apply reads it and puts it on the board.
3. On the application, **Write it** for the resume and the cover letter. Your model writes them in the
   background. A claim check then flags anything your profile doesn't say. Fix it, or say "It's true".
   **Preview** shows it in your template, as it will be downloaded: **Download PDF**, or the page itself.
   To change how your documents look, go to **Settings → Document templates**. Download a template,
   change its HTML and CSS, and upload it. It's checked first: it must be safe and pass WCAG 2.2 AA.
4. **The kit** on each application: open the form, download the PDFs, copy your saved answers. When you've
   sent it, press "I've submitted it".
5. Optional: **Sources** and **Searches** to have listings found and scored for you each morning (see
   [Sources](sources.md)).

## Help on every page

The **?** beside each page's title, and beside each part of a page, opens that part's guide beside it.

## Language and appearance

Everything is in English, Nepali and Spanish (Settings → Language). Light and dark
follow your system. The sidebar's button beside the name collapses it to icons. The sidebar stays in place
while the page scrolls.
