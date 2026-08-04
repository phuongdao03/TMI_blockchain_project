from collections import Counter
from dataclasses import dataclass
from threading import Lock
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CatalogMetricSnapshot:
    cache_operations: dict[str, int]
    cache_duration_seconds: float

    @property
    def cache_hit_ratio(self) -> float:
        hits = sum(
            value
            for key, value in self.cache_operations.items()
            if key.endswith(":hit")
        )
        misses = sum(
            value
            for key, value in self.cache_operations.items()
            if key.endswith(":miss")
        )
        return hits / (hits + misses) if hits + misses else 0.0


class CatalogTelemetry(Protocol):
    def record_cache(
        self, *, scope: str, outcome: str, duration_seconds: float
    ) -> None: ...


class InProcessCatalogTelemetry:
    """Process-local adapter for metrics exporters and operational diagnostics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._operations: Counter[str] = Counter()
        self._duration_seconds = 0.0

    def record_cache(
        self, *, scope: str, outcome: str, duration_seconds: float
    ) -> None:
        with self._lock:
            self._operations[f"{scope}:{outcome}"] += 1
            self._duration_seconds += max(duration_seconds, 0.0)

    def snapshot(self) -> CatalogMetricSnapshot:
        with self._lock:
            return CatalogMetricSnapshot(
                cache_operations=dict(self._operations),
                cache_duration_seconds=self._duration_seconds,
            )

    def reset(self) -> None:
        with self._lock:
            self._operations.clear()
            self._duration_seconds = 0.0


catalog_telemetry = InProcessCatalogTelemetry()
