from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SearchHistoryItem:
    id: UUID
    display_query: str
    searched_at: datetime


@dataclass(frozen=True, slots=True)
class SearchHistoryState:
    is_enabled: bool
    items: tuple[SearchHistoryItem, ...]
