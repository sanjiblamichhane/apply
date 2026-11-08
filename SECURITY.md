# Security

apply holds people's profiles, documents and, with Auto, the power to send applications. Please report
weaknesses privately, so they can be fixed before anyone else learns of them.

## Reporting

Use the repository's **private vulnerability reporting**
([Security → Report a vulnerability](https://github.com/sanjiblamichhane/apply/security/advisories/new)); reports go
to the maintainer, [@sanjiblamichhane](https://github.com/sanjiblamichhane). Don't
open a public issue, discussion or pull request about a vulnerability. Say what you found, how to reproduce it,
and what it lets someone do. We'll acknowledge it within a week and keep you told until it's fixed, with credit
if you'd like it.

## In scope

- Getting at another account's data, or acting as it (owner isolation, sessions, API tokens and their scopes).
- Getting around the Origin check, or the network restrictions on fetching pages (SSRF).
- Script injection through pasted or fetched pages, documents, PDFs or the extension.
- Making Auto send something the person didn't let it, or get around its gate, hold or Pause.
- Secrets in logs, errors, exports or images.

## Out of scope

- Running apply on a public address without `APPLY_ALLOW_REMOTE=1` and HTTPS, against the README's
  advice.
- What your own model writes: the claim check flags it, and you review it before anything is sent.
- Attacks that need control of the machine apply runs on.
