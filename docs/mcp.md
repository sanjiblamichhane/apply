# AI agents (MCP)

`apply mcp` lets an AI agent use your apply as a tool, through the Model Context Protocol (MCP). Claude Desktop,
Claude Code, Cursor and other MCP clients start it and talk to it over stdin and stdout. It talks to apply's API
with a token you make for it, never to the database.

**apply drafts and fills. You review and submit.** An agent's token can track postings, read your applications,
profile and saved answers, and ask apply to write a draft resume or cover letter. It can't record a submission,
send anything, change or delete an application, change your profile or touch your account. Private answers
(equal-opportunity questions) are never given to it: they go into a form, not to a model.

## Tools

| Tool | What it does |
| --- | --- |
| `who_am_i` | Checks the connection: whose apply this is, and what the token may do. |
| `list_applications` | Your applications, newest first, with their stage and documents. |
| `add_opportunity` | Tracks a posting from its link or text and starts an application for it. |
| `find_application_by_url` | Whether apply already tracks the posting at a link. |
| `get_application` | One application: the posting, the values for its form, your saved answers, its documents. |
| `get_profile` | Your profile, section by section, as you'd paste it. |
| `write_document` | Asks apply to write a draft (a resume or cover letter) on your own model. |
| `get_document` | A document's text (Markdown), its status, and the lines to check against your profile. |

## 1. Make a token for the agent

In apply, **Settings → Extension and AI agents**, choose **An AI agent**, then **Make a token**. Or on the
command line:

```sh
docker exec apply-api apply token --kind agent --name "My AI app"   # with the containers
uv run apply token --kind agent --name "My AI app"                  # from source, in services/backend
```

The token is shown once. Revoke it in Settings whenever you like.

## 2. Add apply to your MCP client

With apply running in its containers (`docker compose up`), the client runs `apply mcp` inside the `apply-api`
container. It finds the API there on its own; `-e APPLY_TOKEN` passes the token in.

**Claude Desktop** (Settings → Developer → Edit Config, `claude_desktop_config.json`) and **Cursor**
(`~/.cursor/mcp.json`, or `.cursor/mcp.json` in a project) use the same shape:

```json
{
  "mcpServers": {
    "apply": {
      "command": "docker",
      "args": ["exec", "-i", "-e", "APPLY_TOKEN", "apply-api", "apply", "mcp"],
      "env": { "APPLY_TOKEN": "apl_…" }
    }
  }
}
```

**Claude Code:**

```sh
claude mcp add apply --env APPLY_TOKEN=apl_… -- docker exec -i -e APPLY_TOKEN apply-api apply mcp
```

Restart the client, then ask it something like "Which applications do I have in progress?" or "Track this job
and draft a cover letter for it: https://…".

### From source

Run it with uv from your checkout instead, and point it at the API with `APPLY_URL` (by default
`http://127.0.0.1:8110`):

```json
{
  "mcpServers": {
    "apply": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/apply/services/backend", "apply", "mcp"],
      "env": { "APPLY_TOKEN": "apl_…", "APPLY_URL": "http://127.0.0.1:8110" }
    }
  }
}
```

For Claude Code: `claude mcp add apply --env APPLY_TOKEN=apl_… -- uv run --directory /path/to/apply/services/backend apply mcp`.

## Settings

| Variable | Default | |
| --- | --- | --- |
| `APPLY_TOKEN` | (required) | An agent token (`apl_…`). |
| `APPLY_URL` | `http://127.0.0.1:8110` | apply's API. Inside the `apply-api` container that's the API itself. |

If a tool says the token is unknown, revoked or expired, make a new one. A document takes a while to write on
a local model: the agent asks `get_document` again until it's ready.
