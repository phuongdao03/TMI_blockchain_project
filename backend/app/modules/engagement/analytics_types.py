from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EngagementAnalyticsSnapshotView:
    id: UUID
    metric_date: date
    generated_at: datetime
    unique_views: int
    share_events: int
    qr_scans: int
    report_requests: int
    favorite_events: int
