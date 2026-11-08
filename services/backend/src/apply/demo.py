"""
The demo: John Doe, a fictional profile with a few applications at different stages, their documents already
written (lorem ipsum: nothing is asked of a model), a search with two scored matches, and a saved answer.

Offered when an account is made (POST /auth/register with ``demo``), and as ``apply demo`` for a demo account
from the command line. The data is ``demo/john-doe.json`` at the repo's root, an apply-export/1 file loaded with
the ordinary import (so the demo also shows import works). Its dates move so the newest is now. Every name is
invented, and every link goes to example.com.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from apply.errors import Conflict, ErrorCode, InvalidArgument, NotFound
from apply.logic.auth import create_owner
from apply.logic.portable import ImportReport, PortableExport, import_
from apply.store.sql import Database
from apply.store.sql.models import User

SOURCE = "apply-demo"
_HERE = Path(__file__).resolve()
# The repo's demo/ when run from source; /app/demo in the image (compose gives the build the demo/ folder).
# Any folder above this file (the repo when run from source, /app in the image), then the working directory.
CANDIDATES = (*(folder / "demo" / "john-doe.json" for folder in _HERE.parents), Path.cwd() / "demo" / "john-doe.json")
_WHEN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def demo_file() -> Path:
    for path in CANDIDATES:
        if path.is_file():
            return path
    raise NotFound(ErrorCode.NOT_FOUND, "The demo data (demo/john-doe.json) isn't here")


def _times(value: Any) -> list[datetime]:
    if isinstance(value, dict):
        return [t for v in value.values() for t in _times(v)]
    if isinstance(value, list):
        return [t for v in value for t in _times(v)]
    if isinstance(value, str) and _WHEN.match(value):
        return [datetime.fromisoformat(value.replace("Z", "+00:00"))]
    return []


def _moved(value: Any, by: timedelta) -> Any:
    if isinstance(value, dict):
        return {k: _moved(v, by) for k, v in value.items()}
    if isinstance(value, list):
        return [_moved(v, by) for v in value]
    if isinstance(value, str) and _WHEN.match(value):
        return (datetime.fromisoformat(value.replace("Z", "+00:00")) + by).isoformat()
    return value


def demo_data(now: datetime | None = None) -> PortableExport:
    """The demo, its dates moved so the newest is ``now``."""
    raw = json.loads(demo_file().read_text(encoding="utf-8"))
    newest = max(_times(raw))
    return PortableExport.model_validate(_moved(raw, (now or datetime.now(UTC)) - newest))


async def add_to(db: Database, user_id: str) -> ImportReport:
    """Put the demo in an account (the person asked for it when making the account)."""
    async with db.transaction() as session:
        return await import_(session, user_id, demo_data(), source=SOURCE)


async def install(db: Database, email: str, password: str | None, *, force: bool = False) -> ImportReport:
    """
    Make the demo account and fill it. On a database with any account already, only with ``force``, and then
    into the existing account ``email`` (which must exist): the demo never mixes into someone's data by accident.
    """
    async with db.transaction() as session:
        accounts = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    if accounts and not force:
        raise Conflict(ErrorCode.OWNER_EXISTS, "This database has accounts already")
    if not accounts:
        if not password:
            raise InvalidArgument(ErrorCode.VALIDATION_FAILED, "A password is needed for the demo account")
        await create_owner(db, email, password)
    async with db.transaction() as session:
        user = (await session.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
        if user is None:
            raise NotFound(ErrorCode.NOT_FOUND, f"No account {email}")
        return await import_(session, user.id, demo_data(), source=SOURCE)
