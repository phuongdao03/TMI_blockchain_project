"use client";

import {
  BadgeCheck,
  BadgeDollarSign,
  Bell,
  BookOpen,
  CalendarDays,
  ClipboardCheck,
  Clock3,
  FileCheck2,
  FileText,
  Gauge,
  CircleHelp,
  History,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  Signature,
  UsersRound,
  Building2,
  MapPinned,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuthUser } from "@/lib/auth/user-context";
import {
  resolveWorkspacePersona,
  type WorkspacePersona,
} from "@/lib/auth/role-workspaces";
import { cn } from "@/lib/utils";
import { IconFrame } from "@/components/ui/icon-frame";
import { isPreviewRelease, isPreviewRestrictedPath } from "@/lib/release-mode";

type NavigationItem = {
  href: string;
  label: string;
  icon: typeof Gauge;
  permission?: string;
  allowedRoles?: readonly string[];
};

type NavigationSection = {
  label: string;
  items: NavigationItem[];
};

const discoveryItems: NavigationItem[] = [
  { href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/search", label: "Tìm đề cử", icon: Search },
  { href: "/works", label: "Thư viện đề cử", icon: BookOpen },
  { href: "/verify", label: "Tra cứu chứng thư", icon: ShieldCheck },
];

const personalItems: NavigationItem[] = [
  { href: "/notifications", label: "Thông báo", icon: Bell },
  { href: "/account", label: "Tài khoản", icon: Settings },
  { href: "/activity", label: "Hoạt động gần đây", icon: History },
];

const publicSupportItem: NavigationItem = {
  href: "/guide",
  label: "Hướng dẫn",
  icon: CircleHelp,
};

const adminSupportItem: NavigationItem = {
  href: "/admin/guide",
  label: "Hướng dẫn",
  icon: CircleHelp,
};

const userItems: NavigationItem[] = [
  { href: "/dossiers", label: "Hồ sơ của tôi", icon: FileText },
  { href: "/certificates", label: "Chứng thư", icon: FileCheck2 },
];

const reviewerItems: NavigationItem[] = [
  {
    href: "/work-allocations",
    label: "Công việc được giao",
    icon: ClipboardCheck,
  },
  { href: "/attendance", label: "Chấm công", icon: Clock3 },
  { href: "/leave", label: "Nghỉ phép", icon: CalendarDays },
  { href: "/overtime", label: "Tăng ca", icon: Clock3 },
];

const employeeItems: NavigationItem[] = reviewerItems.slice(1);

const adminItems: NavigationItem[] = [
  {
    href: "/admin/work-allocations",
    label: "Phân công công việc",
    icon: ClipboardCheck,
    permission: "work.allocations.manage",
    allowedRoles: ["SUPER_ADMIN"],
  },
  {
    href: "/admin/overtime",
    label: "Duyệt tăng ca",
    icon: Clock3,
    permission: "hr.overtime.read",
  },
  {
    href: "/admin/leave",
    label: "Duyệt nghỉ phép",
    icon: CalendarDays,
    permission: "hr.leave.read",
  },
  {
    href: "/admin/attendance",
    label: "Chấm công",
    icon: Clock3,
    permission: "hr.attendance.read",
  },
  {
    href: "/admin/attendance/worksites",
    label: "Điểm chấm công",
    icon: MapPinned,
    permission: "hr.attendance.worksites.manage",
  },
  {
    href: "/admin/payroll",
    label: "Bảng lương",
    icon: BadgeDollarSign,
    permission: "hr.payroll.read",
  },
  {
    href: "/admin/employees",
    label: "Nhân viên",
    icon: UsersRound,
    permission: "hr.employees.read",
  },
  {
    href: "/admin/departments",
    label: "Phòng ban",
    icon: Building2,
    permission: "hr.departments.manage",
  },
  {
    href: "/admin/payments",
    label: "Tài chính",
    icon: BadgeDollarSign,
    permission: "payments.read",
  },
  {
    href: "/admin/dashboard",
    label: "Tổng quan vận hành",
    icon: Gauge,
    permission: "dashboard.read",
  },
  {
    href: "/admin/users",
    label: "Người dùng",
    icon: UsersRound,
    permission: "users.read",
  },
  {
    href: "/admin/staff",
    label: "Tài khoản nhân sự",
    icon: UsersRound,
    permission: "staff.read",
  },
  {
    href: "/admin/content",
    label: "Nội dung công bố",
    icon: FileText,
    permission: "public_content.manage",
  },
  {
    href: "/admin/certificates",
    label: "Quản lý chứng thư",
    icon: BadgeCheck,
    permission: "public_content.manage",
  },
  {
    href: "/admin/audit",
    label: "Lịch sử hoạt động",
    icon: History,
    permission: "audit.read",
  },
  {
    href: "/admin/reports",
    label: "Báo cáo",
    icon: FileCheck2,
    permission: "reports.read",
  },
];

const blockchainSignerItems: NavigationItem[] = [
  {
    href: "/blockchain",
    label: "Ký blockchain",
    icon: Signature,
    permission: "blockchain.sign",
  },
];

function canAccess(
  item: NavigationItem,
  roles: readonly string[],
  permissions: readonly string[],
): boolean {
  return (
    (!item.allowedRoles ||
      item.allowedRoles.some((role) => roles.includes(role))) &&
    (!item.permission ||
      roles.includes("SUPER_ADMIN") ||
      permissions.includes(item.permission))
  );
}

function sectionsFor(
  persona: WorkspacePersona,
  roles: readonly string[],
  permissions: readonly string[],
  isEmployee: boolean,
): NavigationSection[] {
  const operationalItems = adminItems.filter((item) =>
    canAccess(item, roles, permissions),
  );
  if (persona === "SUPER_ADMIN") {
    return [
      { label: "Điều hành", items: adminItems },
      { label: "Tra cứu", items: discoveryItems.slice(1) },
      { label: "Cá nhân", items: personalItems.slice(0, 2) },
    ];
  }

  if (persona === "MODERATOR") {
    return [
      ...(operationalItems.length
        ? [{ label: "Vận hành", items: operationalItems }]
        : []),
      { label: "Công việc", items: reviewerItems },
      { label: "Tra cứu", items: discoveryItems.slice(1) },
      { label: "Cá nhân", items: personalItems.slice(0, 2) },
    ];
  }

  return [
    ...(operationalItems.length
      ? [{ label: "Vận hành", items: operationalItems }]
      : []),
    { label: "Khám phá", items: discoveryItems },
    ...(persona === "USER" ? [{ label: "Hồ sơ", items: userItems }] : []),
    ...(persona === "USER" && isEmployee
      ? [{ label: "Nhân sự", items: employeeItems }]
      : []),
    { label: "Cá nhân", items: personalItems },
  ];
}

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

function mobileItemsFor(
  persona: WorkspacePersona,
  items: NavigationItem[],
): NavigationItem[] {
  const operational = items.filter(
    (item) => item.href.startsWith("/admin/") || item.href === "/blockchain",
  );
  const priorities: Record<WorkspacePersona, string[]> = {
    VIEWER: ["/dashboard", "/search", "/works"],
    USER: ["/dashboard", "/dossiers", "/attendance", "/leave"],
    MODERATOR: ["/work-allocations", "/attendance", "/leave", "/overtime"],
    SUPER_ADMIN: [
      "/admin/dashboard",
      "/admin/work-allocations",
      "/admin/payroll",
      "/blockchain",
      "/admin/payments",
      "/admin/leave",
      "/admin/overtime",
      "/notifications",
    ],
  };
  const byHref = new globalThis.Map(items.map((item) => [item.href, item]));
  const prioritized = [
    ...priorities[persona].map((href) => byHref.get(href)),
    ...operational,
  ].filter((item): item is NavigationItem => item !== undefined);
  const uniquePrioritized = prioritized.filter(
    (item, index) =>
      prioritized.findIndex((candidate) => candidate.href === item.href) ===
      index,
  );
  const remaining = items.filter(
    (item) =>
      !uniquePrioritized.some((candidate) => candidate.href === item.href),
  );
  return [...uniquePrioritized, ...remaining].slice(0, 4);
}

export function DashboardNavigation({
  roles,
  className,
  showPrimaryNavigation = true,
  showQuickNavigation = true,
  previewRole,
  previewPathname,
  onNavigate,
  onOpenMenu,
}: {
  roles?: readonly string[];
  className?: string;
  tone?: "light" | "dark";
  showPrimaryNavigation?: boolean;
  showQuickNavigation?: boolean;
  previewRole?: WorkspacePersona;
  previewPathname?: string;
  onNavigate?: () => void;
  onOpenMenu?: (trigger: HTMLButtonElement) => void;
}) {
  const pathname = usePathname();
  const activePathname = previewRole ? (previewPathname ?? pathname) : pathname;
  const authUser = useAuthUser();
  const effectiveRoles = roles ?? authUser?.roles ?? [];
  const effectivePermissions = authUser?.permissions ?? [];
  const isEmployee = authUser?.isEmployee ?? previewRole === "USER";
  const persona = resolveWorkspacePersona(effectiveRoles);
  const preview = isPreviewRelease();
  const supportItem =
    persona === "SUPER_ADMIN" ? adminSupportItem : publicSupportItem;
  const sections = [
    ...sectionsFor(persona, effectiveRoles, effectivePermissions, isEmployee),
    { label: "Hỗ trợ", items: [supportItem] },
    ...(effectiveRoles.includes("SUPER_ADMIN")
      ? [{ label: "Blockchain", items: blockchainSignerItems }]
      : []),
  ].map((section) => ({
    ...section,
    items: section.items.filter(
      (item) =>
        canAccess(item, effectiveRoles, effectivePermissions) &&
        (!preview || !isPreviewRestrictedPath(item.href)),
    ),
  }));

  const allNavigationItems = sections.flatMap((section) => section.items);
  const activeHref = allNavigationItems
    .filter((item) => isActive(activePathname, item.href))
    .sort((left, right) => right.href.length - left.href.length)[0]?.href;
  const mobileItems = mobileItemsFor(persona, allNavigationItems);
  const mobileHrefs = new Set(mobileItems.map((item) => item.href));
  const mobileMenuContainsActiveItem = allNavigationItems
    .filter((item) => !mobileHrefs.has(item.href))
    .some((item) => item.href === activeHref);

  return (
    <>
      {showPrimaryNavigation ? (
        <nav
          className={cn("dashboard-navigation", className)}
          aria-label="Điều hướng"
        >
          {sections.map((section) =>
            section.items.length ? (
              <section
                className="dashboard-navigation__section"
                key={section.label}
              >
                <p className="dashboard-navigation__label">{section.label}</p>
                <div className="dashboard-navigation__links">
                  {section.items.map((item) => {
                    const Icon = item.icon;
                    const active = item.href === activeHref;
                    const content = (
                      <>
                        <IconFrame
                          icon={Icon}
                          size="sm"
                          tone={active ? "inverse" : "neutral"}
                        />
                        <span>{item.label}</span>
                      </>
                    );
                    return (
                      <Link
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "dashboard-navigation__link",
                          active && "dashboard-navigation__link--active",
                        )}
                        href={
                          previewRole
                            ? `/ui-preview?role=${previewRole}&path=${encodeURIComponent(item.href)}`
                            : item.href
                        }
                        key={item.href}
                        onClick={onNavigate}
                      >
                        {content}
                      </Link>
                    );
                  })}
                </div>
              </section>
            ) : null,
          )}
        </nav>
      ) : null}

      {showQuickNavigation ? (
        <nav
          className="dashboard-mobile-navigation"
          aria-label="Điều hướng nhanh"
        >
          {mobileItems.map((item) => {
            const Icon = item.icon;
            const active = item.href === activeHref;
            const content = (
              <>
                <IconFrame
                  className="dashboard-mobile-navigation__icon"
                  icon={Icon}
                  size="sm"
                  tone={active ? "brand" : "neutral"}
                />
                <span className="dashboard-mobile-navigation__label">
                  {item.label}
                </span>
              </>
            );
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={cn(
                  "dashboard-mobile-navigation__link",
                  active && "dashboard-mobile-navigation__link--active",
                )}
                href={
                  previewRole
                    ? `/ui-preview?role=${previewRole}&path=${encodeURIComponent(item.href)}`
                    : item.href
                }
                key={item.href}
                onClick={onNavigate}
              >
                {content}
              </Link>
            );
          })}
          {!previewRole ? (
            <button
              aria-current={mobileMenuContainsActiveItem ? "page" : undefined}
              aria-label="Mở tất cả chức năng"
              className={cn(
                "dashboard-mobile-navigation__link",
                "dashboard-mobile-navigation__more",
                mobileMenuContainsActiveItem &&
                  "dashboard-mobile-navigation__link--active",
              )}
              onClick={(event) => onOpenMenu?.(event.currentTarget)}
              type="button"
            >
              <IconFrame
                className="dashboard-mobile-navigation__icon"
                icon={Menu}
                size="sm"
                tone={mobileMenuContainsActiveItem ? "brand" : "neutral"}
              />
              <span className="dashboard-mobile-navigation__label">Thêm</span>
            </button>
          ) : null}
        </nav>
      ) : null}
    </>
  );
}
