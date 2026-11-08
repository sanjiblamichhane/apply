# The browser extension

The browser extension keeps your apply profile in your browser's side panel, beside any page.

**Copy** (what it shows first) lists your profile in tabs: Basics, Experience, Education, More and Answers, with
one search across them all. Click a value and it's on the clipboard; paste it into the form. Forms' ways of
asking are ready to paste: first, middle and last name; the address line by line; the phone with its country
code; each job's dates also as 01/2021 and 2021-01; skills with commas or one per line. Equal-opportunity
answers stay hidden until you press **Show**. The panel never touches the page, so it works on every site and
needs no permission for it. It keeps your profiles in memory only, and they're gone when the browser closes.

It's built so you rarely scroll. One row at the top holds the profile (a list with its own search) and every
tool: search, refresh, Copy (the clipboard), Fill (the magic wand) and Settings, each named in a tooltip. The
section tabs wrap rather than hide, the values add columns as the panel widens, and each job folds to one line.
`/` opens the search, and **Enter** copies the first match. The language, the theme (Match the system, Light or
Dark), the clipboard setting and Disconnect are under **Settings** (the gear).

**Clear the clipboard a minute after copying** (in Settings) is off by default. Turning it on asks your browser for the clipboard
permissions. It clears only what apply copied, and only if that's still on the clipboard. It can't reach
your system's clipboard history, a clipboard synced between devices, or a clipboard manager.

**Fill**, on the application forms of the supported job boards (listed by address in
`services/frontend/packages/ats-adapters/src/boards.json`), fills in your profile,
attaches your PDFs and puts in your saved answers. On any other site, **Use apply on this site** asks your
browser for that one site. Before writing anything, it shows what it would put in each field (equal-opportunity
answers hidden until you show them): untick any you'd rather fill yourself, then press **Fill the form**.
**Check the form again** (↻ at the top) reads the form afresh with your latest profile and answers.
Anything it isn't sure of is left blank and listed. A board's own dropdowns are
listed with the answer to choose. **You** check the form and press its Submit button: the extension never
does. When the board says thank you, it records the submission and moves the application along, with Undo.

## Install

```sh
cd services/frontend && pnpm --filter @apply/extension build    # → apps/extension/dist
```

In your browser's extensions page (`chrome://extensions`) → Developer mode → **Load unpacked** → `services/frontend/apps/extension/dist`.
Then in apply, **Settings → Extension and AI agents → Make a token**, and paste it into the extension's panel.

The extension asks only for the side panel, its own storage, the supported job boards and apply's address. Its
token can read your profiles, read and track applications, and record submissions, nothing else, and you can
revoke it in Settings. A token made before November 2026 can't read profiles: make a new one, then disconnect
and connect again in the panel.
