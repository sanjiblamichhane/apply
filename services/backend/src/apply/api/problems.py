"""
Turning failures into answers. Whatever goes wrong in a request (our own errors, a body that doesn't fit the
schema, an unknown path, the database, a bug) leaves as one RFC 9457 problem document with a stable ``code``.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, ProgrammingError
from starlette.exceptions import HTTPException

from apply.errors import ApplyError, ErrorCode, InvalidArgument, MethodNotAllowed, NotFound, Unavailable

log = logging.getLogger("apply.api")
MEDIA_TYPE = "application/problem+json"


def answer(error: ApplyError, **override: object) -> JSONResponse:
    body = error.as_problem(**override)
    return JSONResponse(body, status_code=body["status"], media_type=MEDIA_TYPE, headers=error.headers)


async def _ours(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApplyError)
    if exc.status >= 500:
        log.error("request failed: %s", exc)
    return answer(exc)


async def _unfit(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Where and why only: what was sent is never echoed back (it may be a password).
    where = [
        {
            "loc": [part if isinstance(part, int) else str(part) for part in item.get("loc", ())],
            "msg": str(item.get("msg", "")),
            "type": str(item.get("type", "")),
        }
        for item in exc.errors()
    ]
    return answer(
        InvalidArgument(ErrorCode.VALIDATION_FAILED, "The request doesn't fit the API", extra={"errors": where})
    )


async def _routing(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    if exc.status_code == 404:
        return answer(NotFound(ErrorCode.NOT_FOUND, "No such path"))
    if exc.status_code == 405:
        return answer(MethodNotAllowed(detail="That method is not allowed here"))
    return answer(ApplyError(ErrorCode.INTERNAL, str(exc.detail)), status=exc.status_code)


async def _database(_: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, ProgrammingError) and "does not exist" in str(exc.orig):
        log.error("the database needs migrating: %s", exc.orig)
        return answer(Unavailable(ErrorCode.DATABASE_NOT_READY, "Run: apply migrate"))
    log.exception("database failure")
    return answer(ApplyError(ErrorCode.INTERNAL, "Database error"))


async def _bug(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled exception")
    return answer(ApplyError(ErrorCode.INTERNAL, "Something went wrong"))


def answer_failures_as_problems(app: FastAPI) -> None:
    for kind, handler in (
        (ApplyError, _ours),
        (RequestValidationError, _unfit),
        (HTTPException, _routing),
        (DBAPIError, _database),
        (Exception, _bug),
    ):
        app.add_exception_handler(kind, handler)
