from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.search.history_types import SearchHistoryItem, SearchHistoryState


class SearchHistorySchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda name: (
            name.split("_")[0]
            + "".join(part.capitalize() for part in name.split("_")[1:])
        ),
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class SearchHistoryItemData(SearchHistorySchema):
    id: UUID
    display_query: str
    searched_at: datetime

    @classmethod
    def from_item(cls, item: SearchHistoryItem) -> "SearchHistoryItemData":
        return cls.model_validate(item, from_attributes=True)


class SearchHistoryData(SearchHistorySchema):
    is_enabled: bool
    items: list[SearchHistoryItemData]

    @classmethod
    def from_state(cls, state: SearchHistoryState) -> "SearchHistoryData":
        return cls(
            is_enabled=state.is_enabled,
            items=[SearchHistoryItemData.from_item(item) for item in state.items],
        )


class SearchHistoryConsentRequest(SearchHistorySchema):
    is_enabled: bool


class SearchHistoryRecordRequest(SearchHistorySchema):
    query: str = Field(min_length=2, max_length=200)


class SearchHistoryRecordedData(SearchHistorySchema):
    recorded: bool
