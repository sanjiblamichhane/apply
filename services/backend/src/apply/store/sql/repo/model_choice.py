"""The model chosen in Settings → Model: one row for the install, or none."""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ModelChoiceRow

CURRENT = "current"


async def get(session: AsyncSession) -> ModelChoiceRow | None:
    return await session.get(ModelChoiceRow, CURRENT)


async def put(session: AsyncSession, **values: object) -> ModelChoiceRow:
    row = await session.get(ModelChoiceRow, CURRENT, with_for_update=True)
    if row is None:
        row = ModelChoiceRow(id=CURRENT, **values)
        session.add(row)
    else:
        for name, value in values.items():
            setattr(row, name, value)
    await session.flush()
    return row


async def clear(session: AsyncSession) -> None:
    await session.execute(delete(ModelChoiceRow).where(ModelChoiceRow.id == CURRENT))
