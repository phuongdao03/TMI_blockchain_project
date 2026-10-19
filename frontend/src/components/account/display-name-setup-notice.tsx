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
      className="border-b border-[var(--theme-border)] bg-[var(--theme-accent)]/5 px-5 py-2.5"
      role="status"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5 text-sm text-[var(--theme-text)]">
          <UserRound
            aria-hidden="true"
            className="size-4 shrink-0 text-[var(--theme-accent)]"
          />
          <p>
            <span className="font-medium">
              Thêm tên hiển thị để tham gia cộng đồng.
            </span>
          </p>
        </div>
        <Link
          className="inline-flex min-h-10 shrink-0 items-center text-sm font-semibold text-[var(--theme-accent)] underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href="/account"
        >
          Thiết lập
        </Link>
      </div>
    </div>
  );
}
