from typing import Literal

from pydantic import BaseModel, ConfigDict


class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str


class ListResponseMeta(ResponseMeta):
    model_config = ConfigDict(
        alias_generator=lambda name: "".join(
            part.capitalize() if index else part
            for index, part in enumerate(name.split("_"))
        ),
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )

    page: int
    page_size: int
    total: int


class SuccessEnvelope[DataT](BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: DataT
    meta: ResponseMeta


class PaginatedSuccessEnvelope[DataT](BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: DataT
    meta: ListResponseMeta


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, object]
    request_id: str


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[False] = False
    error: ErrorBody


class HealthData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    status: Literal["ok"]


class ReadinessData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dependencies: dict[str, Literal["up", "down"]]
    status: Literal["ready"]
