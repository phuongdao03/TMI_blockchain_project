from collections import Counter
from threading import Lock


class EngagementAnalyticsTelemetry:
    """Process-local counters exposed to the configured metrics exporter."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._outcomes: Counter[str] = Counter()

    def record(self, outcome: str) -> None:
        with self._lock:
            self._outcomes[outcome] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._outcomes)

    def reset(self) -> None:
        with self._lock:
            self._outcomes.clear()


engagement_analytics_telemetry = EngagementAnalyticsTelemetry()
