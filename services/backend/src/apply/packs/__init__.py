"""
The packs apply knows: built in (job, tender, grant, contract), and any installed package registering one under
the ``apply.packs`` entry point (``[project.entry-points."apply.packs"] tender = "apply_tender:TenderPack"``).
"""

import logging
from functools import cache
from importlib.metadata import entry_points

from apply.errors import ErrorCode, NotFound

from .base import Pack
from .contract import ContractPack
from .grant import GrantPack
from .job import JobPack
from .tender import TenderPack

logger = logging.getLogger("apply.packs")
BUILT_IN: tuple[type[Pack], ...] = (JobPack, TenderPack, GrantPack, ContractPack)
DEFAULT_PACK = "job"  # what a request means when it names no pack: the only place the engine names one


@cache
def all_packs() -> dict[str, Pack]:
    packs: dict[str, Pack] = {cls.key: cls() for cls in BUILT_IN}
    for entry in entry_points(group="apply.packs"):
        try:
            cls = entry.load()
            pack = cls()
        except Exception:
            logger.exception("packs: could not load %s from %s", entry.name, entry.value)
            continue
        if pack.key in packs:
            logger.warning("packs: %s is already registered; ignoring %s", pack.key, entry.value)
            continue
        packs[pack.key] = pack
    return packs


def get_pack(key: str) -> Pack:
    try:
        return all_packs()[key]
    except KeyError:
        raise NotFound(ErrorCode.PACK_NOT_FOUND, f"No pack {key!r}") from None


__all__ = ["BUILT_IN", "DEFAULT_PACK", "Pack", "all_packs", "get_pack"]
