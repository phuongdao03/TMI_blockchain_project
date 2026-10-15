import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { CommunitySavedPosts } from "@/components/community/community-saved-posts";
import { getServerAuthState } from "@/lib/auth/server-session";

export const metadata: Metadata = {
  title: "Bài đã lưu · Cộng đồng",
  robots: { index: false, follow: false },
};

export default async function CommunitySavedPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const authState = await getServerAuthState();
  if (!authState.user && !authState.hasRefreshCookie) {
    redirect(`/login?next=${encodeURIComponent("/community/saved")}`);
  }
  const input = await searchParams;
  const pageValue = Number(singleValue(input.page));
  const page = Number.isFinite(pageValue)
    ? Math.max(1, Math.min(10_000, Math.floor(pageValue)))
    : 1;
  return <CommunitySavedPosts page={page} />;
}

function singleValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
