"""
Files (PDFs, Auto's screenshots, uploaded resumes) in an object storage bucket, never on the local disk, so any
number of API and worker processes, on any machine, see the same files.

    files = Storage(StorageConfig(bucket="apply", endpoint=CLOUD_ENDPOINT))
    await files.put("owners/01H…/documents/01H…/ab12….pdf", pdf, "application/pdf")
    data = await files.get("owners/01H…/documents/01H…/ab12….pdf")  # None when there isn't one

At ``CLOUD_ENDPOINT`` (the hosted service) the client library's default credentials are used: the service
account the API and worker run as, or a key file the library is pointed at. Any other endpoint is a storage
emulator (compose.yml runs one; the tests start one) and is reached without credentials.

The client library is synchronous: every call runs in a thread, with one client per thread.
"""

import asyncio
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any

CLOUD_ENDPOINT = "https://storage.googleapis.com"
TIMEOUT = 60.0  # seconds, per call


class StorageError(Exception):
    """The bucket couldn't be reached, doesn't exist, or refused the call."""


@dataclass(frozen=True)
class StorageConfig:
    bucket: str
    endpoint: str = CLOUD_ENDPOINT
    project: str = ""  # only the emulator needs one; the hosted service uses the credentials' project
    create_bucket: bool = (
        False  # the emulator's bucket is made on start; a real one is made by whoever runs the service
    )
    retry_seconds: float = 20.0  # how long a call keeps retrying a passing error before it's a StorageError

    @property
    def emulated(self) -> bool:
        return self.endpoint.rstrip("/") != CLOUD_ENDPOINT


@dataclass(frozen=True)
class StoredFile:
    key: str
    size: int
    updated: datetime | None


class Storage:
    def __init__(self, config: StorageConfig) -> None:
        self.config = config
        self._local = threading.local()

    # ── the client, one per thread ───────────────────────────────────────────

    def _retry(self) -> Any:
        """The library's own retry (passing errors only, backing off), for no longer than retry_seconds."""
        from google.cloud.storage.retry import DEFAULT_RETRY

        return DEFAULT_RETRY.with_timeout(self.config.retry_seconds) if self.config.retry_seconds else None

    def _bucket(self) -> Any:
        bucket = getattr(self._local, "bucket", None)
        if bucket is None:
            from google.cloud import storage

            if self.config.emulated:
                from google.auth.credentials import AnonymousCredentials

                client = storage.Client(
                    project=self.config.project or "apply-local",
                    credentials=AnonymousCredentials(),
                    client_options={"api_endpoint": self.config.endpoint.rstrip("/")},
                )
            else:
                client = storage.Client(project=self.config.project or None)
            bucket = self._local.bucket = client.bucket(self.config.bucket)
        return bucket

    async def _run(self, fn: Any, *args: Any) -> Any:
        from google.api_core import exceptions
        from google.auth import exceptions as auth_exceptions

        try:
            return await asyncio.to_thread(fn, *args)
        except (exceptions.GoogleAPIError, auth_exceptions.GoogleAuthError, OSError) as exc:
            raise StorageError(f"{type(exc).__name__}: {exc}") from exc

    # ── files ────────────────────────────────────────────────────────────────

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Keep ``data`` at ``key``, replacing what was there (keys name their content, so a retry is safe)."""

        def put() -> None:
            blob = self._bucket().blob(key)
            blob.cache_control = "private, no-store"
            blob.upload_from_string(data, content_type=content_type, timeout=TIMEOUT, retry=self._retry())

        await self._run(put)

    async def get(self, key: str) -> bytes | None:
        from google.api_core.exceptions import NotFound

        def get() -> bytes | None:
            try:
                return self._bucket().blob(key).download_as_bytes(timeout=TIMEOUT, retry=self._retry())
            except NotFound:
                return None

        return await self._run(get)

    async def delete(self, *keys: str) -> None:
        """Remove these; one that isn't there is fine."""
        from google.api_core.exceptions import NotFound

        def delete() -> None:
            bucket = self._bucket()
            for key in keys:
                try:
                    bucket.blob(key).delete(timeout=TIMEOUT, retry=self._retry())
                except NotFound:
                    pass

        if keys:
            await self._run(delete)

    async def files(self, prefix: str) -> list[StoredFile]:
        def list_() -> list[StoredFile]:
            bucket = self._bucket()
            return [
                StoredFile(key=b.name, size=b.size or 0, updated=b.updated)
                for b in bucket.client.list_blobs(bucket, prefix=prefix, timeout=TIMEOUT, retry=self._retry())
            ]

        return await self._run(list_)

    async def delete_prefix(self, prefix: str) -> int:
        found = await self.files(prefix)
        await self.delete(*(f.key for f in found))
        return len(found)

    # ── the bucket ───────────────────────────────────────────────────────────

    async def ensure(self, *, retry: bool = True) -> None:
        """The bucket is there (the emulator's is made when ``create_bucket``); StorageError if not."""
        from google.api_core.exceptions import Conflict, NotFound

        def ensure() -> None:
            bucket = self._bucket()
            try:
                bucket.reload(timeout=TIMEOUT if retry else 5.0, retry=self._retry() if retry else None)
            except NotFound:
                if not self.config.create_bucket:
                    raise StorageError(
                        f"The bucket {self.config.bucket!r} doesn't exist at {self.config.endpoint}. Create it, or "
                        "set APPLY_STORAGE_BUCKET to one that does."
                    ) from None
                try:
                    bucket.client.create_bucket(self.config.bucket, timeout=TIMEOUT, retry=self._retry())
                except Conflict:
                    pass  # made by another process just now

        await self._run(ensure)

    async def reachable(self) -> bool:
        """For /health: one quick try, no retries."""
        try:
            await self.ensure(retry=False)
        except StorageError:
            return False
        return True


# ── where each kind of file goes: everything of one account under owners/<id>/ ──


def document_file(owner_id: str, document_id: str, sha256: str, kind: str) -> str:
    """A document version as a file: ``kind`` is its extension (pdf, html)."""
    return f"owners/{owner_id}/documents/{document_id}/{sha256}.{kind}"


def document_pdf(owner_id: str, document_id: str, sha256: str) -> str:
    return document_file(owner_id, document_id, sha256, "pdf")


def screenshot(owner_id: str, run_id: str, screenshot_id: str) -> str:
    return f"owners/{owner_id}/auto/{run_id}/{screenshot_id}.png"


def profile_source(owner_id: str, profile_id: str, extension: str) -> str:
    return f"owners/{owner_id}/profiles/{profile_id}/source{extension}"


__all__ = [
    "CLOUD_ENDPOINT",
    "Storage",
    "StorageConfig",
    "StorageError",
    "StoredFile",
    "document_file",
    "document_pdf",
    "profile_source",
    "screenshot",
]
