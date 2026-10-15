import type { Metadata } from "next";

import { CommunityMemberProfile } from "@/components/community/community-member-profile";

export const metadata: Metadata = {
  title: "Thành viên · Cộng đồng",
};

export default async function CommunityMemberPage({
  params,
  searchParams,
}: {
  params: Promise<{ username: string }>;
  searchParams: Promise<{ page?: string | string[]; view?: string | string[] }>;
}) {
  const [{ username }, input] = await Promise.all([params, searchParams]);
  const pageValue = Number(singleValue(input.page));
  const page = Number.isFinite(pageValue)
    ? Math.max(1, Math.min(10_000, Math.floor(pageValue)))
    : 1;
  const viewValue = singleValue(input.view);
  const view = viewValue === "followers" || viewValue === "following" ? viewValue : "posts";
  return <CommunityMemberProfile page={page} username={username} view={view} />;
}

function singleValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
