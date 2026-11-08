"""
The test suites' throwaway Postgres and bucket: compose.test.yml, as a project with a fixed name, so every
container and network it makes is named and nothing is left behind (no anonymous volumes: the database is in a
tmpfs). ``down -v`` first clears whatever an interrupted run left.

    with Stack("apply-test-backend") as stack:
        stack.database_url, stack.storage_url
"""

import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # the repo
COMPOSE_FILE = ROOT / "compose.test.yml"


class Stack:
    def __init__(self, name: str) -> None:
        self.name = name
        self.env = {**os.environ, "APPLY_TEST_STACK": name}

    def _compose(self, *args: str) -> str:
        return subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), "-p", self.name, *args],
            check=True,
            capture_output=True,
            text=True,
            env=self.env,
        ).stdout.strip()

    def _port(self, service: str, port: int) -> str:
        return self._compose("port", service, str(port)).rsplit(":", 1)[-1]

    def up(self) -> "Stack":
        self.down()
        self._compose("up", "-d", "--wait", "postgres", "storage")
        db_port = self._port("postgres", 5432)
        self.database_url = f"postgresql+asyncpg://apply:apply-test@127.0.0.1:{db_port}/apply"
        self.storage_url = f"http://127.0.0.1:{self._port('storage', 4443)}"
        deadline = time.monotonic() + 30
        while True:  # the emulator has no health check of its own
            try:
                urllib.request.urlopen(f"{self.storage_url}/storage/v1/b", timeout=2).close()
                break
            except (urllib.error.URLError, OSError):
                if time.monotonic() > deadline:
                    raise RuntimeError(f"{self.name}: the bucket emulator didn't start") from None
                time.sleep(0.2)
        return self

    def down(self) -> None:
        self._compose("down", "-v", "--remove-orphans")

    def __enter__(self) -> "Stack":
        return self.up()

    def __exit__(self, *_exc: object) -> None:
        self.down()
