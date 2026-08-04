from uuid import UUID

from app.modules.public.schemas import PublicSchema


class RankingRecountData(PublicSchema):
    campaign_id: UUID
    status: str
