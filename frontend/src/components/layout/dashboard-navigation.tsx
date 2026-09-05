"use client";

import {
  BadgeDollarSign,
  Bell,
  BookOpen,
  FileCheck2,
  FileText,
  Gauge,
  CircleHelp,
  History,
  LayoutDashboard,
  Map,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  Signature,
  UsersRound,
  Vote,
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
};

type NavigationSection = {
  label: string;
  items: NavigationItem[];
};

const discoveryItems: NavigationItem[] = [
  { href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/search", label: "Tìm đề cử", icon: Search },
  { href: "/works", label: "Thư viện đề cử", icon: BookOpen },
  { href: "/map", label: "Bản đồ đề cử", icon: Map },
  { href: "/verify", label: "Tra cứu chứng thư", icon: ShieldCheck },
];

const personalItems: NavigationItem[] = [
  { href: "/notifications", label: "Thông báo", icon: Bell },
  { href: "/account", label: "Tài khoản", icon: Settings },
  { href: "/vote-history", label: "Bình chọn của tôi", icon: Vote },
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
  { href: "/reviews", label: "Hồ sơ đánh giá", icon: FileCheck2 },
];

const adminItems: NavigationItem[] = [
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
    !item.permission ||
    roles.includes("SUPER_ADMIN") ||
    permissions.includes(item.permission)
  );
}

function sectionsFor(
  persona: WorkspacePersona,
  roles: readonly string[],
  permissions: readonly string[],
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
    VIEWER: ["/dashboard", "/search", "/works", "/map"],
    USER: ["/dashboard", "/dossiers", "/notifications", "/search"],
    MODERATOR: ["/reviews", "/notifications", "/search", "/works"],
    SUPER_ADMIN: [
      "/admin/dashboard",
      "/admin/payments",
      "/blockchain",
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
  onNavigate,
  onOpenMenu,
}: {
  roles?: readonly string[];
  className?: string;
  tone?: "light" | "dark";
  showPrimaryNavigation?: boolean;
  showQuickNavigation?: boolean;
  onNavigate?: () => void;
  onOpenMenu?: (trigger: HTMLButtonElement) => void;
}) {
  const pathname = usePathname();
  const authUser = useAuthUser();
  const effectiveRoles = roles ?? authUser?.roles ?? [];
  const effectivePermissions = authUser?.permissions ?? [];
  const persona = resolveWorkspacePersona(effectiveRoles);
  const preview = isPreviewRelease();
  const supportItem =
    persona === "SUPER_ADMIN" ? adminSupportItem : publicSupportItem;
  const sections = [
    ...sectionsFor(persona, effectiveRoles, effectivePermissions),
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
  const mobileItems = mobileItemsFor(persona, allNavigationItems);
  const mobileHrefs = new Set(mobileItems.map((item) => item.href));
  const mobileMenuContainsActiveItem = allNavigationItems
    .filter((item) => !mobileHrefs.has(item.href))
    .some((item) => isActive(pathname, item.href));

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
                    const active = isActive(pathname, item.href);
                    return (
                      <Link
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "dashboard-navigation__link",
                          active && "dashboard-navigation__link--active",
                        )}
                        href={item.href}
                        key={item.href}
                        onClick={onNavigate}
                      >
                        <IconFrame
                          icon={Icon}
                          size="sm"
                          tone={active ? "inverse" : "neutral"}
                        />
                        <span>{item.label}</span>
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
            const active = isActive(pathname, item.href);
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={cn(
                  "dashboard-mobile-navigation__link",
                  active && "dashboard-mobile-navigation__link--active",
                )}
                href={item.href}
                key={item.href}
                onClick={onNavigate}
              >
                <IconFrame
                  icon={Icon}
                  size="sm"
                  tone={active ? "brand" : "neutral"}
                />
                <span>{item.label}</span>
              </Link>
            );
          })}
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
              icon={Menu}
              size="sm"
              tone={mobileMenuContainsActiveItem ? "brand" : "neutral"}
            />
            <span>Thêm</span>
          </button>
        </nav>
      ) : null}
    </>
  );
}
