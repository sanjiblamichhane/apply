#!/usr/bin/env bash
# The live suite: the same journeys against the real model (your local model server), on a throwaway database. Prints timings.
# (No board's own pages are opened by a script: only their public APIs, with APPLY_LIVE_SOURCES=1.)
#
#   APPLY_LIVE_LLM_MODEL=<a model your server has> tests/live.sh
#   APPLY_LIVE_LLM_BASE_URL=http://gpu-box:11434 APPLY_LIVE_LLM_MODEL=<model> tests/live.sh
#   APPLY_LIVE_SOURCES=1 tests/live.sh     # also read each real source once (job boards, Contracts Finder, Grants.gov)
set -euo pipefail
cd "$(dirname "$0")/../services/backend"
APPLY_LIVE=1 uv run pytest tests/live -q -s "$@"
