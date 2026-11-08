"""
What a running apply holds: settings, the database, the model, the fetcher, the queue and the file bucket. One
per process, shared by the API (app.state.runtime) and the worker, and built by the tests with fakes where they
need them.
"""

from dataclasses import dataclass

from apply import __version__
from apply.libs.extract import FetchConfig, Fetcher
from apply.libs.jobs import Queue
from apply.libs.llm import LanguageModel, SwitchableModel
from apply.libs.storage import CLOUD_ENDPOINT, Storage, StorageConfig
from apply.settings import AppSettings
from apply.store.sql import Database
from apply.store.sql.models import jobs


@dataclass
class Runtime:
    settings: AppSettings
    db: Database
    model: LanguageModel
    fetcher: Fetcher
    queue: Queue
    files: Storage

    @classmethod
    def create(
        cls,
        settings: AppSettings,
        *,
        model: LanguageModel | None = None,
        fetcher: Fetcher | None = None,
        files: Storage | None = None,
    ) -> "Runtime":
        db = Database(settings.database_url, pool_size=settings.database_pool_size)
        # The model chosen in Settings → Model (read on every call), else the settings'.
        from apply.logic import model_choice

        model = model or SwitchableModel(
            model_choice.from_settings(settings), lambda: model_choice.load(db), timeout=settings.llm_timeout
        )
        fetcher = fetcher or Fetcher(
            FetchConfig(
                version=__version__,
                timeout=settings.fetch_timeout,
                max_bytes=settings.fetch_max_bytes,
                max_json_bytes=settings.fetch_max_json_bytes,
                allow_private=settings.fetch_allow_private,
            )
        )
        files = files or Storage(
            StorageConfig(
                bucket=settings.storage_bucket,
                endpoint=settings.storage_endpoint,
                project=settings.storage_project,
                create_bucket=settings.storage_endpoint.rstrip("/") != CLOUD_ENDPOINT,
            )
        )
        return cls(settings=settings, db=db, model=model, fetcher=fetcher, queue=Queue(db.engine, jobs), files=files)

    async def aclose(self) -> None:
        close = getattr(self.model, "aclose", None)
        if close is not None:
            await close()
        await self.fetcher.aclose()
        await self.db.dispose()
