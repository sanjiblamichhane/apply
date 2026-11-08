#!/usr/bin/env bash
# Every check that runs without the real model: lint, formatting, and all backend suites (unit, db, api) on
# throwaway Postgres databases; the Turborepo's lint, typecheck and unit tests; then the browser journeys
# (Playwright: the web app, and the browser extension in a test browser, against the real backend and worker on
# their own throwaway databases and ports).
# A container runtime must be running: each suite starts its own named stack from compose.test.yml and removes it after.
#
#   tests/check.sh            everything
#   tests/check.sh backend    the backend only
#   tests/check.sh web        the Turborepo only (lint, typecheck, unit tests, browser journeys)
#   tests/check.sh fast       everything but the browser journeys
set -euo pipefail
cd "$(dirname "$0")/.."
root=$(pwd)
what=${1:-all}

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

if [[ $what == all || $what == backend || $what == fast ]]; then
  cd "$root/services/backend"
  step "backend: ruff check"
  uv run ruff check .
  step "backend: ruff format --check"
  uv run ruff format --check .
  step "backend: OpenAPI schema is current"
  uv run apply openapi --out /tmp/apply-openapi.json
  diff -q openapi.json /tmp/apply-openapi.json >/dev/null || {
    echo "openapi.json is out of date: run (cd services/backend && uv run apply openapi --out openapi.json)"; exit 1; }
  step "backend: unit tests"
  uv run pytest tests/unit -q
  step "backend: database tests (throwaway Postgres)"
  uv run pytest tests/db -q
  step "backend: API end-to-end tests (throwaway Postgres, fake model, real worker)"
  uv run pytest tests/api -q
  cd "$root"
  step "brand: the logo and icons are what tools/draw_mark.py and the theme say"
  uv run --no-project --with pytest pytest tools/tests -q -p no:cacheprovider
fi

if [[ $what == all || $what == web || $what == fast ]]; then
  cd "$root/services/frontend"
  step "frontend: install"
  pnpm install --frozen-lockfile --silent
  step "frontend: API types are current with openapi.json"
  pnpm --filter @apply/api exec node scripts/generate.mjs --check
  step "frontend: lint (TypeScript, React hooks, jsx-a11y)"
  pnpm lint
  step "frontend: typecheck and unit tests (i18n, contrast, kit, api, ats-adapters, extension, web)"
  pnpm test
fi

if [[ $what == all || $what == web ]]; then
  cd "$root/services/frontend/apps/web"
  step "web: browser journeys (Playwright + axe, throwaway database, ports 3399/8199)"
  pnpm exec playwright install chromium >/dev/null
  pnpm exec playwright test --reporter=line
  cd "$root/services/frontend/apps/extension"
  step "extension: journeys in a test browser (the unpacked test build, fake boards, throwaway database, API port 8198)"
  pnpm exec playwright test --reporter=line
fi

# A maintainer's own extra checks, kept outside the repo in the git-ignored .local/ folder, run when present.
if [[ -x "$root/.local/check" ]]; then
  step "local checks"
  "$root/.local/check"
fi

step "all green"
