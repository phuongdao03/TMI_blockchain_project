import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { CommunityMinePosts } from "@/components/community/community-mine-posts";
import { getServerAuthState } from "@/lib/auth/server-session";
import type { CommunityOwnerPostStatus } from "@/lib/api/types";

export const metadata: Metadata = {
  title: "Bài viết của tôi · Cộng đồng",
  robots: { index: false, follow: false },
};

export default async function CommunityMinePage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string | string[]; page?: string | string[] }>;
}) {
  const authState = await getServerAuthState();
  const input = await searchParams;
  const status = one(input.status);
  const page = parsePage(one(input.page));
  const safeStatus = isOwnerStatus(status) ? status : undefined;
  const minePath = `/community/mine?${new URLSearchParams({
    ...(safeStatus ? { status: safeStatus } : {}),
    page: String(page),
  }).toString()}`;

  if (!authState.user && !authState.hasRefreshCookie) {
    redirect(`/login?next=${encodeURIComponent(minePath)}`);
  }
  return <CommunityMinePosts status={safeStatus} page={page} />;
}

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function parsePage(value: string | undefined): number {
  const page = Number(value);
  return Number.isFinite(page) ? Math.max(1, Math.min(10_000, Math.floor(page))) : 1;
}

function isOwnerStatus(value: string | undefined): value is CommunityOwnerPostStatus {
  return value === "DRAFT" || value === "PENDING" || value === "PUBLISHED" || value === "REJECTED";
}
