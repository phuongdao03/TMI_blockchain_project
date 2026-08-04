from collections import Counter
from threading import Lock


class VotingLifecycleTelemetry:
    """Process-local lifecycle metrics adapter for the configured exporter."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._transitions: Counter[str] = Counter()

    def record(self, outcome: str) -> None:
        with self._lock:
            self._transitions[outcome] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._transitions)

    def reset(self) -> None:
        with self._lock:
            self._transitions.clear()


voting_lifecycle_telemetry = VotingLifecycleTelemetry()
