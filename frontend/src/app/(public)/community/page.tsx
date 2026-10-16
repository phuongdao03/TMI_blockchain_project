import type { Metadata } from "next";

import { CommunityFeed } from "@/components/community/community-feed";
import type { CommunityPostSort } from "@/lib/api/types";

export const metadata: Metadata = {
  title: "Cộng đồng",
  description:
    "Chia sẻ câu chuyện, ý tưởng và trải nghiệm cùng cộng đồng Tinh Hoa Việt.",
  alternates: { canonical: "/community" },
};

export default async function CommunityPage({
  searchParams,
}: {
  searchParams: Promise<{
    category?: string | string[];
    relatedWorkId?: string | string[];
    q?: string | string[];
    sort?: string | string[];
    page?: string | string[];
  }>;
}) {
  const input = await searchParams;
  const category = normalizedFilter(input.category, 100);
  const relatedWorkId = normalizedFilter(input.relatedWorkId, 100);
  const q = normalizedFilter(input.q, 120);
  const requestedSort = singleValue(input.sort);
  const sort: CommunityPostSort = isCommunityPostSort(requestedSort)
    ? requestedSort
    : "recent";
  const pageValue = Number(singleValue(input.page));
  const page = Number.isFinite(pageValue)
    ? Math.max(1, Math.min(10_000, Math.floor(pageValue)))
    : 1;

  return (
    <CommunityFeed
      category={category}
      relatedWorkId={relatedWorkId}
      q={q}
      sort={sort}
      page={page}
    />
  );
}

function singleValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function normalizedFilter(
  value: string | string[] | undefined,
  maxLength: number,
): string | undefined {
  return singleValue(value)?.trim().slice(0, maxLength) || undefined;
}

function isCommunityPostSort(
  value: string | undefined,
): value is CommunityPostSort {
  return (
    value === "recent" ||
    value === "popular" ||
    value === "discussed" ||
    value === "following"
  );
}
