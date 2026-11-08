"""
Job boards for the browser tests: the recorded API shapes (tests/support/boards.py) on a local port.

    python -m tests.support.e2e_boards --port 18435
"""

import argparse
import json

import uvicorn

from .boards import BOARD01, BOARD02, BOARD03
from .servers import Site


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    site = Site()
    for boards in (BOARD01, BOARD02, BOARD03):
        for path, body in boards.items():
            site.add(path, json.dumps(body), content_type="application/json")
    uvicorn.run(site.app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
