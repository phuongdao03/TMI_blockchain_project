from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.cms.models import CmsContentStatus


class CmsPostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    title: Annotated[str, Field(min_length=1, max_length=255)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=180)]
    excerpt: Annotated[str | None, Field(max_length=500)] = None
    body_html: Annotated[str, Field(alias="bodyHtml", min_length=1, max_length=100_000)]
    category_id: UUID | None = Field(default=None, alias="categoryId")

    @field_validator("title", "excerpt")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CmsPostData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=True
    )
    id: UUID
    title: str
    slug: str
    excerpt: str | None
    body_html: str = Field(alias="bodyHtml")
    category_id: UUID | None = Field(alias="categoryId")
    status: CmsContentStatus
    version: int
    published_at: datetime | None = Field(alias="publishedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class CmsPageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    title: Annotated[str, Field(min_length=1, max_length=255)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=180)]
    body_html: Annotated[str, Field(alias="bodyHtml", min_length=1, max_length=100_000)]


class CmsPageData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=True
    )
    id: UUID
    title: str
    slug: str
    body_html: str = Field(alias="bodyHtml")
    status: CmsContentStatus
    version: int
    published_at: datetime | None = Field(alias="publishedAt")


class CmsBannerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    title: Annotated[str, Field(min_length=1, max_length=255)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=180)]
    image_url: Annotated[str, Field(alias="imageUrl", min_length=1, max_length=1000)]
    link_url: Annotated[str | None, Field(alias="linkUrl", max_length=1000)] = None


class CmsBannerData(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, serialize_by_alias=True
    )
    id: UUID
    title: str
    slug: str
    image_url: str = Field(alias="imageUrl")
    link_url: str | None = Field(alias="linkUrl")
    status: CmsContentStatus
    version: int
    published_at: datetime | None = Field(alias="publishedAt")


class CmsCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, Field(min_length=1, max_length=160)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=160)]
    description: Annotated[str | None, Field(max_length=2000)] = None


class CmsCategoryData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str
    description: str | None


class CmsStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: CmsContentStatus
