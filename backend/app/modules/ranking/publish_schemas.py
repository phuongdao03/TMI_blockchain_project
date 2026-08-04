from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.modules.public.schemas import PublicSchema


class RankingPublishRequest(PublicSchema):
    version: Annotated[int, Field(gt=0)]


class RankingPublicationData(PublicSchema):
    campaign_id: UUID
    snapshot_id: UUID
    version: int
    published_at: datetime
