"use client";

import { Menu } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import type { RefObject } from "react";

import { LogoutButton } from "@/components/auth/logout-button";
import {
  CommunityRoleBadge,
  getAuthenticatedCommunityIdentity,
} from "@/components/community/community-user-identity";
import { MembershipAccountAvatar } from "@/components/membership/membership-account-avatar";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { PwaInstallButton } from "@/components/pwa/pwa-install-button";
import { profileApi } from "@/lib/api/client";
import type { AuthUser } from "@/lib/api/types";

const pageTitles: Record<string, string> = {
  "/workspace": "Không gian cá nhân",
  "/dashboard": "Tổng quan",
  "/account": "Tài khoản",
  "/membership": "Thẻ thành viên",
  "/wallet": "Ví của tôi",
  "/activity": "Hoạt động gần đây",
  "/certificates": "Bằng xác lập",
  "/dossiers": "Hồ sơ của tôi",
  "/notifications": "Thông báo",
  "/work-allocations": "Công việc được giao",
  "/reviews": "Hàng đợi thẩm định",
  "/admin": "Quản trị hệ thống",
  "/admin/dashboard": "Tổng quan vận hành",
  "/admin/memberships": "Gói thành viên",
  "/admin/notifications": "Gửi thông báo",
  "/admin/work-allocations": "Phân công công việc",
  "/admin/payroll": "Bảng lương",
  "/admin/reviews": "Phân công thẩm định",
  "/admin/content": "Quản trị nội dung",
  "/admin/staff": "Nhân sự",
  "/admin/employees": "Nhân sự",
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
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
    enabled: Boolean(user),
    staleTime: 60_000,
  });
  const identity = getAuthenticatedCommunityIdentity({
    displayName: profile.data?.displayName,
    roles: user?.roles,
    permissions: user?.permissions,
  });
  const avatarUrl = profile.data?.avatarMediaId
    ? `/api/v1/community/avatars/${encodeURIComponent(profile.data.avatarMediaId)}`
    : profile.data?.avatarUrl;
  const navigationContext = pathname.startsWith("/admin")
    ? "quản trị"
    : "workspace";

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

      <div className="dashboard-context-header__actions flex shrink-0 items-center gap-2">
        <button
          aria-controls={
            navigationOpen ? "dashboard-workspace-navigation" : undefined
          }
          aria-expanded={navigationOpen}
          aria-label={`Mở điều hướng ${navigationContext}`}
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
        <PwaInstallButton className="dashboard-context-header__install" />
        {user ? (
          <div className="hidden max-w-64 items-center gap-2 md:flex">
            <MembershipAccountAvatar
              displayName={identity.displayName}
              size={28}
              src={avatarUrl}
              user={user}
            />
            <span className="max-w-40 truncate text-sm text-[var(--theme-muted)]">
              {identity.displayName}
            </span>
            <CommunityRoleBadge
              isAdmin={identity.isAdmin}
              roleLabel={identity.roleLabel}
            />
          </div>
        ) : null}
        {user ? <NotificationBell /> : null}
        <div className="dashboard-context-header__desktop-account">
          <ThemeToggle />
          {user ? <LogoutButton /> : null}
        </div>
      </div>
    </header>
  );
}
