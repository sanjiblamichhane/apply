"""
Settings, all from the environment (``APPLY_*``) or a ``.env`` file next to where apply runs.

The defaults run apply on one machine: the API on 127.0.0.1, the development Postgres from compose.yml,
and a local model server on its usual port. Nothing here is read from a request.
"""

import ipaddress
from functools import cached_property
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


# What .env.example puts where a secret goes: refused, so a copied example never runs as-is.
PLACEHOLDER = "changeme"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APPLY_", env_file=".env", extra="ignore", env_ignore_empty=True)

    env: Literal["development", "test", "production"] = "development"

    # Database: Postgres only.
    # No password here: set APPLY_DATABASE_URL (services/backend/.env) with the one in the repo's .env.
    database_url: str = "postgresql+asyncpg://apply@127.0.0.1:54329/apply"
    database_pool_size: int = Field(default=5, ge=1, le=100)

    # The API. Bound to this machine unless allow_remote says otherwise (see README, "Exposing apply").
    host: str = "127.0.0.1"
    port: int = Field(default=8110, ge=1, le=65535)
    allow_remote: bool = False
    # The web app's "Create your account": open only until the owner exists (then closed for good). Turn it off
    # to make the owner with `apply init` only, as on a server others can reach before you've set it up.
    web_setup: bool = True
    # Origins a browser may send unsafe requests from (the web app), besides the API's own.
    allowed_origins: list[str] = ["http://localhost:3310", "http://127.0.0.1:3310"]

    # Sessions
    session_days: int = Field(default=30, ge=1, le=365)
    cookie_secure: bool | None = None  # None: Secure everywhere except on a local address
    sign_in_max_failures: int = Field(default=5, ge=1)
    sign_in_lock_minutes: int = Field(default=15, ge=1)
    # How long a "Forgot your password?" link works.
    reset_minutes: int = Field(default=30, ge=5, le=24 * 60)

    # The web app's address, for links in emails. Never taken from a request (its Host could be anyone's).
    public_url: str = "http://localhost:3310"

    # Email (password resets), over SMTP. No host: apply sends none, and "Forgot your password?" says to ask
    # the owner. compose.yml points this at a local mail catcher, which keeps every message on this machine.
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: Literal["starttls", "tls", "none"] = "starttls"
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_timeout: float = Field(default=15.0, gt=0)
    mail_from: str = "apply <apply@localhost>"

    # The model, until one is chosen in Settings → Model: a local model server at llm_base_url, speaking the
    # "native" API (/api/chat) or the "v1" API (/v1/chat/completions). No model is assumed: name one here, or choose
    # one in Settings → Model.
    llm_api: Literal["native", "v1"] = "native"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = ""
    llm_writing_model: str = ""
    llm_timeout: float = Field(default=180.0, gt=0)
    llm_num_ctx: int = Field(default=16384, ge=2048)
    # Where Settings → Model looks for other local servers: these ports on llm_base_url's host, never elsewhere.
    # {} looks at llm_base_url only.
    llm_discover_ports: list[int] = Field(default_factory=lambda: [11434, 1234, 8080, 1337, 8000])

    # Fetching a pasted link.
    fetch_timeout: float = Field(default=10.0, gt=0)
    fetch_max_bytes: int = Field(default=3_000_000, ge=10_000)
    fetch_max_json_bytes: int = Field(default=30_000_000, ge=10_000)  # a job board's whole listing
    fetch_allow_private: bool = False  # tests serve pages from 127.0.0.1; never on in normal use

    # Documents.
    pdf_paper: Literal["a4", "us-letter"] = "us-letter"  # for a template without its own @page

    # Files (PDFs, Auto's screenshots, uploaded resumes): an object storage bucket, never the local disk. For the
    # hosted service, set the endpoint to libs.storage.CLOUD_ENDPOINT (the service's own credentials are used) and
    # the bucket to one that exists. Any other endpoint is a storage emulator, reached without credentials: compose.yml
    # runs one on 127.0.0.1:4453, and its bucket is made on start.
    storage_endpoint: str = "http://127.0.0.1:4453"
    storage_bucket: str = Field(default="apply", min_length=3, max_length=63, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    storage_project: str = ""
    # Uploading a resume to make a profile.
    upload_max_bytes: int = Field(default=5_000_000, ge=10_000, le=50_000_000)

    # The worker.
    worker_poll_seconds: float = Field(default=2.0, gt=0)
    scheduler_tick_seconds: float = Field(default=60.0, gt=0)

    # Discovery.
    score_daily_cap: int = Field(default=200, ge=0)  # fit scores per owner per day (a few seconds each on an 8B model)
    # Where each source's API lives; only tests change these (to serve recorded answers from this machine).
    source_base_urls: dict[str, str] = Field(default_factory=dict)

    # Auto.
    auto_poll_seconds: float = Field(default=5.0, gt=0)  # how often a run looks again while documents are written
    auto_wait_minutes: float = Field(default=45.0, gt=0)  # how long a run may wait for its documents

    @model_validator(mode="after")
    def _check(self) -> "AppSettings":
        if not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("APPLY_DATABASE_URL must be a postgresql+asyncpg:// URL: apply runs on Postgres only.")
        if urlsplit(self.database_url).password == PLACEHOLDER:
            raise ValueError(
                f"The database password is still '{PLACEHOLDER}' from .env.example. Set POSTGRES_PASSWORD in .env to a "
                "long random one (openssl rand -hex 24)."
            )
        if urlsplit(self.public_url).scheme not in ("http", "https") or not urlsplit(self.public_url).hostname:
            raise ValueError(f"APPLY_PUBLIC_URL={self.public_url} is not the web app's http(s) address.")
        if not self.is_local_host(self.host) and not self.allow_remote:
            raise ValueError(
                f"APPLY_HOST={self.host} would expose apply beyond this machine. "
                "Set APPLY_ALLOW_REMOTE=1 if that is what you want (see README, 'Exposing apply')."
            )
        return self

    @staticmethod
    def is_local_host(host: str) -> bool:
        if host in LOCAL_HOSTS:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    @property
    def mail_enabled(self) -> bool:
        return bool(self.smtp_host)

    @cached_property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return not self.is_local_host(self.host)

    @cached_property
    def own_origins(self) -> set[str]:
        """Origins an unsafe browser request may come from: the web app's and the API's own."""
        own = (
            {f"http://{h}:{self.port}" for h in ("localhost", "127.0.0.1")}
            if self.is_local_host(self.host)
            else {f"https://{self.host}", f"http://{self.host}:{self.port}"}
        )
        return own | {o.rstrip("/") for o in self.allowed_origins}
