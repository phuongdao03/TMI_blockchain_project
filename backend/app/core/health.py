import asyncio
import logging
from collections.abc import Mapping
from typing import Literal, Protocol


class DependencyProbe(Protocol):
    async def check(self) -> bool: ...

    async def close(self) -> None: ...


DependencyState = Literal["up", "down"]
logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, probes: Mapping[str, DependencyProbe]) -> None:
        self._probes = dict(probes)

    async def check_readiness(self) -> dict[str, DependencyState]:
        names = sorted(self._probes)
        results = await asyncio.gather(
            *(self._safe_check(self._probes[name]) for name in names)
        )
        states: dict[str, DependencyState] = {
            name: "up" if is_available else "down"
            for name, is_available in zip(names, results, strict=True)
        }
        if "down" in states.values():
            logger.warning("readiness_dependencies_unavailable dependencies=%s", states)
        return states

    async def close(self) -> None:
        await asyncio.gather(*(probe.close() for probe in self._probes.values()))

    @staticmethod
    async def _safe_check(probe: DependencyProbe) -> bool:
        try:
            return await probe.check()
        except Exception:
            return False
