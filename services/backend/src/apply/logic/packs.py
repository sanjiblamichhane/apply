"""
Keeping the packs registry in step with the code: every start-up (API and worker) syncs each installed pack's
row, its default pipeline and its stages. A stage that left the code is archived, not deleted, because
applications and their history may still point at it.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from apply.packs import all_packs
from apply.store.sql.models import Pipeline, Stage
from apply.store.sql.repo import packs as repo


async def sync(session: AsyncSession) -> None:
    await repo.lock_sync(session)
    for pack in all_packs().values():
        await repo.upsert_pack(session, pack.registry_row())
        spec = pack.pipeline
        pipeline = await repo.system_pipeline(session, pack.key, spec.key)
        if pipeline is None:
            pipeline = await repo.add(
                session, Pipeline(pack=pack.key, key=spec.key, label=dict(spec.label), is_default=True, owner_id=None)
            )
        else:
            pipeline.label = dict(spec.label)
            pipeline.is_default = True
        existing = {stage.code: stage for stage in await repo.stages_of(session, pipeline.id)}
        for position, stage_spec in enumerate(spec.stages):
            values = {
                "label": dict(stage_spec.label),
                "position": position,
                "category": stage_spec.category,
                "action_type": stage_spec.action_type,
                "is_terminal": stage_spec.is_terminal,
                "follow_up_after_days": stage_spec.follow_up_after_days,
                "expected_duration_days": stage_spec.expected_duration_days,
                "is_archived": False,
            }
            stage = existing.pop(stage_spec.code, None)
            if stage is None:
                await repo.add(session, Stage(pipeline_id=pipeline.id, code=stage_spec.code, owner_id=None, **values))
            else:
                for key, value in values.items():
                    setattr(stage, key, value)
        for offset, gone in enumerate(sorted(existing.values(), key=lambda s: (s.position, s.code))):
            gone.is_archived = True
            gone.position = len(spec.stages) + offset
    await session.flush()
