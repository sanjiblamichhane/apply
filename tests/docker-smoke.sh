#!/usr/bin/env bash
# The images compose.yml runs: build them (tagged :smoke), start Postgres and a storage emulator, migrate, the API,
# the worker and the web app, and check the web app reaches the API and a file goes to the bucket and back.
# Everything is compose.test.yml's "smoke" profile as the project apply-test-smoke: every container, image and
# network is named, the database is in memory (no volume), and `down -v` removes all of it at the end. Never
# touches the compose stack, its volumes or its ports.
#
#   tests/docker-smoke.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export APPLY_TEST_STACK=apply-test-smoke
web_port=13399
dc() { docker compose -f compose.test.yml -p "$APPLY_TEST_STACK" --profile smoke "$@"; }
# A one-off command in a named container, removed when it ends.
once() { local name=$1; shift; dc run --rm --no-deps --name "apply-test-smoke-$name" "$@"; }

cleanup() { dc down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

echo "== build images"
dc build -q

echo "== start Postgres and the bucket (a storage emulator), migrate, create the owner"
dc up -d --wait postgres storage
once migrate api apply migrate
echo "a long enough password" | once init -T api apply init --email owner@example.com --password-stdin

echo "== start the API, the worker and the web app"
dc up -d api worker web
for _ in $(seq 60); do curl -fs "http://127.0.0.1:$web_port/api/v1/health" >/dev/null 2>&1 && break; sleep 1; done

echo "== check"
curl -fs "http://127.0.0.1:$web_port/api/v1/health" | grep -q '"database":true,"storage":true' || { echo "API or its bucket not reachable through the web app"; exit 1; }
curl -fs -o /dev/null -w '%{http_code}' "http://127.0.0.1:$web_port/sign-in" | grep -q 200 || { echo "sign-in page"; exit 1; }
cookie=$(mktemp)
curl -fs -c "$cookie" -H "Origin: http://127.0.0.1:$web_port" -H 'content-type: application/json' \
  -d '{"email":"owner@example.com","password":"a long enough password"}' "http://127.0.0.1:$web_port/api/v1/auth/sign-in" | grep -q owner@example.com
curl -fs -b "$cookie" "http://127.0.0.1:$web_port/api/v1/packs/job" | grep -q '"key":"job"'
dc logs worker 2>&1 | grep -qi "error" && { dc logs worker; exit 1; } || true
resume=$(mktemp)
printf 'Sam Rai\nBackend Engineer, Himal Tech, 2019 to 2025\n- Built Django REST APIs on PostgreSQL\n' >"$resume"
profile=$(curl -fs -b "$cookie" -H "Origin: http://127.0.0.1:$web_port" -F "file=@$resume;filename=cv.txt" \
  "http://127.0.0.1:$web_port/api/v1/profiles/import" | grep -o '"id":"[0-9A-Z]*"' | head -1 | cut -d'"' -f4)
[ -n "$profile" ] || { echo "uploading a resume failed"; dc logs api; exit 1; }
curl -fs -b "$cookie" "http://127.0.0.1:$web_port/api/v1/profiles/$profile/source" | cmp -s - "$resume" \
  || { echo "the resume didn't come back from the bucket"; exit 1; }
rm -f "$resume" "$cookie"

echo "== all green: images build, migrate, sign in through the web app, packs synced, a file to the bucket and back"
