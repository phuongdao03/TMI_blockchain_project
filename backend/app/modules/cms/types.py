from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CmsPostInput:
    title: str
    slug: str
    excerpt: str | None
    body_html: str
    category_id: UUID | None


@dataclass(frozen=True, slots=True)
class CmsPageInput:
    title: str
    slug: str
    body_html: str


@dataclass(frozen=True, slots=True)
class CmsBannerInput:
    title: str
    slug: str
    image_url: str
    link_url: str | None


@dataclass(frozen=True, slots=True)
class CmsCategoryInput:
    name: str
    slug: str
    description: str | None


@dataclass(frozen=True, slots=True)
class CmsGuideArticleInput:
    title: str
    slug: str
    summary: str
    category: str
    audiences: tuple[str, ...]
    body_html: str
    sort_order: int
