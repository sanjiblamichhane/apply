# Running it yourself

## With compose

`compose.yml` runs Postgres, a file bucket, a local mail catcher (for email), the API, the worker and the web
app, each listening on `127.0.0.1` only. The model is a local model server on the same machine
(`host.docker.internal:11434`): name a model it has as `APPLY_LLM_MODEL` in `.env`, or choose one in
**Settings → Model**.

## The model

apply uses a local model server that speaks one of two APIs: the native API (`/api/chat`, `/api/tags`) or the
v1 API (`/v1/chat/completions`, `/v1/models`). **Settings → Model** lists the servers that answer on this
machine and their models, by address. Choose one there, and optionally a larger one for writing. apply tests a
model before using it, and the choice reaches the API and the worker at once. `apply models` lists the same from
the command line, and `apply check-model` checks the one in use. No model is assumed: until you choose one,
`APPLY_LLM_MODEL` names it.

apply looks only on the host of `APPLY_LLM_BASE_URL`, on the ports local model servers commonly use (11434,
1234, 8080, 1337 and 8000). `APPLY_LLM_DISCOVER_PORTS` changes the list (`[]` looks at `APPLY_LLM_BASE_URL`
only). In a container, that host is `host.docker.internal`. On Linux, a server listening on localhost only
can't be reached from a container: start it on `0.0.0.0` (its "serve on the local network" setting). Nothing is
ever sent beyond this machine, and apply never downloads a model: download one with your model server.

## Files

The files apply makes or is given (each document's page and PDF, Auto's screenshots, the resume a profile was made
from) are kept in an object storage bucket, never on a container's disk. Postgres holds only where each one
is. So any number of API and worker processes, on any machine, see the same files, and a container can be
replaced without losing any.

- **With compose**, the bucket is a local storage emulator (the `storage` service), its files in the `storage`
  volume. Back up that volume along with Postgres's.
- **In the cloud**, use a real bucket, private, in the region you run in:
  1. Make the bucket with uniform access and public access prevented.
  2. Give the service's account read and write access to objects in it (and nothing broader).
  3. Set `APPLY_STORAGE_ENDPOINT` to the storage service's address (for example
     `https://storage.googleapis.com`) and `APPLY_STORAGE_BUCKET=<name>`. apply uses the service's own
     credentials (no key file); elsewhere, `GOOGLE_APPLICATION_CREDENTIALS` points at one.
  apply checks the bucket when it starts and won't start without it. `/api/v1/health` reports
  `"storage": true` while it can reach it.
- Files nobody points at any more (a deleted application's PDFs, say) are removed by the worker every few hours.
- PDFs and screenshots kept in the database by an older version move to the bucket the first time the API or
  the worker starts.

## Email

apply sends one kind of email: the link from **Forgot your password?**. It's plain text, in the account's
language, and the link works once, for 30 minutes (`APPLY_RESET_MINUTES`).

- **With compose**, every email goes to a local mail catcher, which keeps it on this machine. Read it at
  <http://127.0.0.1:8035>. Nothing is sent anywhere.
- **To send real email**, set your email provider's SMTP relay in `.env` (many cloud hosts block outbound
  port 25, so use 587 or 465): `APPLY_SMTP_HOST`, `APPLY_SMTP_PORT`,
  `APPLY_SMTP_SECURITY` (`starttls`, `tls` or `none`), `APPLY_SMTP_USERNAME`, `APPLY_SMTP_PASSWORD` and
  `APPLY_MAIL_FROM`. Set `APPLY_PUBLIC_URL` to the address people open apply at: the link is built from it,
  never from a request.
- **With no SMTP host**, apply sends nothing. "Forgot your password?" then tells people to ask whoever runs it,
  who can set a new password with
  `docker compose run --rm --name apply-password api apply password --email <their email>`.

Whether or not there's an account with the email asked about, the answer is the same, so nobody can learn who
has one. One address can ask 5 times an hour, and an account is sent at most 3 links an hour. A new password
signs that account out everywhere.

## Settings

Settings are `APPLY_*` environment variables (or a `.env` beside the backend); see
`services/backend/src/apply/settings.py`. The ones you're most likely to change:

| Setting | What it does |
|---|---|
| `APPLY_LLM_BASE_URL`, `APPLY_LLM_MODEL` | The model server and model until one is chosen in Settings → Model |
| `APPLY_LLM_API` | `native` (the default: `/api/chat`) or `v1` (`/v1/chat/completions`), the API of the server at `APPLY_LLM_BASE_URL` |
| `APPLY_LLM_WRITING_MODEL`, `APPLY_LLM_NUM_CTX` | A model just for documents; the context size sent to a native-API server |
| `APPLY_LLM_DISCOVER_PORTS` | Where Settings → Model looks (see above) |
| `APPLY_ALLOWED_ORIGINS` | The web app's address(es); requests from anywhere else are refused |
| `APPLY_STORAGE_ENDPOINT`, `APPLY_STORAGE_BUCKET` | The file bucket (see [Files](#files)) |
| `APPLY_UPLOAD_MAX_BYTES` | The largest resume (or other document) a profile can be made from (5 MB) |
| `APPLY_SMTP_HOST`, `APPLY_PUBLIC_URL`, … | Email for password resets (see [Email](#email)) |
| `APPLY_PDF_PAPER` | `us-letter` (the default) or `a4`: the paper for a document template without its own `@page` |
| `APPLY_LANG=ne` or `es` | The command line in Nepali or Spanish (otherwise the system's language, else English) |

## On a network

apply refuses to listen on anything but `127.0.0.1` unless `APPLY_ALLOW_REMOTE=1`. Before you set it, know
that anyone who can reach the port can try to sign in, and your data is behind that one password (sign-ins lock
after repeated failures). Put it behind HTTPS; off localhost, cookies become `Secure` and `__Host-` scoped
automatically. And set `APPLY_ALLOWED_ORIGINS` to the address people use.

`compose.yml` sets `APPLY_COOKIE_SECURE: "0"`, because it serves plain HTTP on localhost. Behind an HTTPS
reverse proxy, change it to `"1"`, so the session cookie is only ever sent over HTTPS.

## Checking an install

`tests/docker-smoke.sh` builds the images and starts everything on a private network with its own ports,
with a local storage emulator for the bucket. It signs in through the web app, sends a file to the bucket and back, and
removes all it made.
