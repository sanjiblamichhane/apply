"""
The FastAPI app. ``create_app(settings)`` for uvicorn and the tests; ``create_app(runtime=…)`` to hand it a
runtime built elsewhere (the tests do, with a fake model or fetcher).

Every failure answers in one shape, RFC 9457 Problem Details with a stable ``code`` (api/schemas.Problem).
Validation errors never echo what was sent (it may be a password).
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from apply import __version__
from apply.api.problems import answer_failures_as_problems
from apply.api.routes import api
from apply.logic import files
from apply.logic import packs as packs_logic
from apply.runtime import Runtime
from apply.settings import AppSettings
from apply.store.sql.migrate import current, head


def _openapi(app: FastAPI) -> dict[str, Any]:
    """FastAPI's schema, with its own 422 shape replaced by ours (every error is a Problem)."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="apply",
        version=__version__,
        routes=app.routes,
        description="The apply API. Errors are RFC 9457 Problem Details with a stable `code`.",
        license_info={"name": "Apache-2.0", "identifier": "Apache-2.0"},
        contact={"name": "sanjiblamichhane", "url": "https://github.com/sanjiblamichhane/apply"},
    )
    problem = {"application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}}
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            responses = operation.get("responses", {})
            responses.pop("422", None)
            for status in ("4XX", "5XX"):
                if status in responses:
                    responses[status]["content"] = problem
    components = schema.get("components", {}).get("schemas", {})
    components.pop("HTTPValidationError", None)
    components.pop("ValidationError", None)
    app.openapi_schema = schema
    return schema


def create_app(
    settings: AppSettings | None = None, *, runtime: Runtime | None = None, close_runtime: bool = True
) -> FastAPI:
    if runtime is None:
        runtime = Runtime.create(settings or AppSettings())
    rt = runtime

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if await current(rt.settings.database_url) != head():
            raise RuntimeError("The database is not migrated. Run: apply migrate")
        async with rt.db.transaction() as session:
            await packs_logic.sync(session)
        await rt.files.ensure()  # the bucket: StorageError (and no start) if it isn't there
        await files.move_from_database(rt)
        yield
        if close_runtime:
            await rt.aclose()

    app = FastAPI(
        title="apply",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.runtime = rt
    answer_failures_as_problems(app)
    app.include_router(api)
    app.openapi = lambda: _openapi(app)  # type: ignore[method-assign]
    return app
