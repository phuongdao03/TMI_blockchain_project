"use client";

import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import type { RefObject } from "react";

import { LogoutButton } from "@/components/auth/logout-button";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { NotificationBell } from "@/components/notifications/notification-bell";
import type { AuthUser } from "@/lib/api/types";

const pageTitles: Record<string, string> = {
  "/dashboard": "Tổng quan",
  "/account": "Tài khoản",
  "/activity": "Hoạt động gần đây",
  "/certificates": "Chứng thư",
  "/dossiers": "Hồ sơ của tôi",
  "/notifications": "Thông báo",
  "/reviews": "Hàng đợi thẩm định",
  "/admin": "Quản trị hệ thống",
  "/admin/dashboard": "Tổng quan vận hành",
  "/admin/content": "Quản trị nội dung",
  "/admin/staff": "Tài khoản nhân sự",
  "/admin/audit": "Lịch sử hoạt động",
  "/admin/reports": "Báo cáo",
};

function resolveTitle(pathname: string): string {
  const exactTitle = pageTitles[pathname];
  if (exactTitle) return exactTitle;

  const matchedPath = Object.keys(pageTitles)
    .filter((path) => path !== "/dashboard" && pathname.startsWith(`${path}/`))
    .sort((left, right) => right.length - left.length)[0];

  return matchedPath
    ? (pageTitles[matchedPath] ?? "Không gian của bạn")
    : "Không gian của bạn";
}

export function DashboardContextHeader({
  user,
  onOpenNavigation,
  navigationButtonRef,
  navigationOpen = false,
}: {
  user: AuthUser | null;
  onOpenNavigation?: () => void;
  navigationButtonRef?: RefObject<HTMLButtonElement | null>;
  navigationOpen?: boolean;
}) {
  const pathname = usePathname();
  const title = resolveTitle(pathname);

  return (
    <header className="dashboard-context-header sticky top-0 z-30 flex min-h-16 items-center justify-between gap-4 border-b border-[var(--theme-line)] bg-[color:var(--theme-surface)] px-5 py-3 lg:px-8">
      <div className="dashboard-context-header__title min-w-0">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--theme-muted)]">
          Đề cử Tinh Hoa Việt
        </p>
        <h1 className="truncate text-lg font-semibold text-[var(--theme-ink)]">
          {title}
        </h1>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          aria-controls={
            navigationOpen ? "dashboard-workspace-navigation" : undefined
          }
          aria-expanded={navigationOpen}
          aria-label="Mở điều hướng workspace"
          className="dashboard-context-header__menu"
          onClick={onOpenNavigation}
          ref={navigationButtonRef}
          type="button"
        >
          <Menu
            aria-hidden="true"
            focusable="false"
            size={20}
            strokeWidth={1.75}
          />
        </button>
        {user?.email ? (
          <span className="hidden max-w-52 truncate text-sm text-[var(--theme-muted)] md:block">
            {user.email}
          </span>
        ) : null}
        {user ? <NotificationBell /> : null}
        <ThemeToggle />
        {user ? <LogoutButton /> : null}
      </div>
    </header>
  );
}
