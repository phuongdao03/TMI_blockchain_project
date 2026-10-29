"use client";

import { useQuery } from "@tanstack/react-query";
import { UserRound, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { profileApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";

export function DisplayNameSetupNotice() {
  const user = useAuthUser();
  const pathname = usePathname() ?? "";
  if (
    !user ||
    !(
      ["/workspace", "/dashboard"].includes(pathname) ||
      pathname.startsWith("/community")
    )
  )
    return null;
  return <NameReminder key={user.id} userId={user.id} />;
}

function NameReminder({ userId }: { userId: string }) {
  const storageKey = `display-name-reminder:${userId}`;
  const [dismissed, setDismissed] = useState(() => {
    try {
      return (
        typeof sessionStorage !== "undefined" &&
        sessionStorage.getItem(storageKey) === "later"
      );
    } catch {
      return false;
    }
  });
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
    enabled: !dismissed,
    staleTime: 60_000,
  });

  if (dismissed || !profile.data || profile.data.displayName?.trim())
    return null;

  return (
    <aside
      className="profile-name-reminder"
      role="note"
      aria-label="Hoàn thiện hồ sơ cá nhân"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5 text-sm text-[var(--theme-text)]">
          <UserRound
            aria-hidden="true"
            className="size-4 shrink-0 text-[var(--theme-accent)]"
          />
          <div>
            <p>
              <span className="font-medium">
                Bạn muốn mọi người gọi mình là gì?
              </span>
            </p>
            <p className="text-sm text-[var(--theme-muted)]">
              Thêm tên hiển thị để dễ nhận ra bạn trong cộng đồng. Bạn vẫn có
              thể chuẩn bị hồ sơ ngay.
            </p>
          </div>
        </div>
        <Link
          className="inline-flex min-h-10 shrink-0 items-center text-sm font-semibold text-[var(--theme-accent)] underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href="/account#display-name"
        >
          Thêm tên
        </Link>
        <button
          type="button"
          aria-label="Để sau"
          className="grid size-11 shrink-0 place-items-center rounded-lg hover:bg-black/5"
          onClick={() => {
            setDismissed(true);
            try {
              sessionStorage.setItem(storageKey, "later");
            } catch {
              /* Optional reminder still closes without storage. */
            }
          }}
        >
          <X aria-hidden="true" className="size-4" />
        </button>
      </div>
    </aside>
  );
}
