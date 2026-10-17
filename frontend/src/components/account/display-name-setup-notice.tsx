"use client";

import { useQuery } from "@tanstack/react-query";
import { UserRound } from "lucide-react";
import Link from "next/link";

import { profileApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";

export function DisplayNameSetupNotice() {
  const user = useAuthUser();
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
    enabled: Boolean(user),
    staleTime: 60_000,
  });

  if (!user || !profile.data || profile.data.displayName?.trim()) return null;

  return (
    <div
      className="border-b border-[var(--theme-border)] bg-[var(--theme-accent)]/5 px-4 py-3"
      role="status"
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-2.5 text-sm text-[var(--theme-text)]">
          <UserRound
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0 text-[var(--theme-accent)]"
          />
          <p>
            <span className="font-bold">Cài đặt tên hiển thị của bạn</span>
            <span className="block text-[var(--theme-muted)]">
              Tên này sẽ xuất hiện cạnh bài viết và bình luận của bạn.
            </span>
          </p>
        </div>
        <Link
          className="inline-flex min-h-10 items-center justify-center self-start rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] sm:self-auto"
          href="/account"
        >
          Cài đặt tên
        </Link>
      </div>
    </div>
  );
}
