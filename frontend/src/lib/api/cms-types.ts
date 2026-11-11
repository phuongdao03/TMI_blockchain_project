export interface CmsPost {
  id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  bodyHtml: string;
  categoryId: string | null;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: number;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CmsPostInput {
  title: string;
  slug: string;
  excerpt?: string | null;
  bodyHtml: string;
  categoryId?: string | null;
}

export type CmsGuideAudience =
  | "PUBLIC"
  | "VIEWER"
  | "USER"
  | "MODERATOR"
  | "SUPER_ADMIN"
  | "EMPLOYEE"
  | "MEMBERSHIP_SILVER"
  | "MEMBERSHIP_COMPANION"
  | "MEMBERSHIP_PRESTIGE";

export type CmsGuideStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";

export interface CmsGuideArticle {
  id: string;
  title: string;
  slug: string;
  summary: string;
  category: string;
  audiences: CmsGuideAudience[];
  bodyHtml: string;
  status: CmsGuideStatus;
  sortOrder: number;
  version: number;
  readingMinutes: number;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CmsGuideArticleInput {
  title: string;
  slug: string;
  summary: string;
  category: string;
  audiences: CmsGuideAudience[];
  bodyHtml: string;
  sortOrder: number;
}

export interface CmsGuideFeedback {
  id: string;
  articleId: string;
  helpful: boolean;
  comment: string | null;
  createdAt: string;
}

export interface CmsGuideListFilters {
  page?: number;
  pageSize?: number;
  query?: string;
  category?: string;
}

export interface CmsGuideAdminFilters extends CmsGuideListFilters {
  status?: CmsGuideStatus;
  audience?: CmsGuideAudience;
}

export interface CmsPage {
  id: string;
  title: string;
  slug: string;
  bodyHtml: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: number;
  publishedAt: string | null;
}

export interface CmsBanner {
  id: string;
  title: string;
  slug: string;
  imageUrl: string;
  linkUrl: string | null;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: number;
  publishedAt: string | null;
}

export interface CmsCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
}
