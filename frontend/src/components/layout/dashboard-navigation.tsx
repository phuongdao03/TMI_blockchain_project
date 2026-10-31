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
  House,
  History,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Signature,
  UsersRound,
  Building2,
  MapPinned,
  Wallet,
  CreditCard,
  Megaphone,
  Ticket,
  ChevronDown,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId, useState } from "react";

import { useAuthUser } from "@/lib/auth/user-context";
import {
  isCustomerAccount,
  resolveWorkspacePersona,
  resolveAdminEntryPoint,
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
  permissions?: readonly string[];
  allowedRoles?: readonly string[];
};

type NavigationSection = {
  label: string;
  items: NavigationItem[];
};

const discoveryItems: NavigationItem[] = [
  { href: "/workspace", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/", label: "Website", icon: House },
  { href: "/works", label: "Thư viện đề cử", icon: BookOpen },
  { href: "/community", label: "Cộng đồng", icon: UsersRound },
  { href: "/events", label: "Sự kiện", icon: CalendarDays },
  { href: "/verify", label: "Tra cứu bằng xác lập", icon: ShieldCheck },
];

const personalItems: NavigationItem[] = [
  { href: "/vouchers", label: "Voucher của tôi", icon: Ticket },
  {
    href: "/advertising",
    label: "Quảng cáo của tôi",
    icon: Megaphone,
    allowedRoles: ["USER", "SUPER_ADMIN"],
  },
  { href: "/notifications", label: "Thông báo", icon: Bell },
  { href: "/account", label: "Tài khoản", icon: Settings },
  { href: "/activity", label: "Hoạt động gần đây", icon: History },
  { href: "/membership", label: "Thẻ thành viên", icon: CreditCard },
  { href: "/wallet", label: "Ví của tôi", icon: Wallet },
];

const publicSupportItem: NavigationItem = {
  href: "/help",
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
  { href: "/certificates", label: "Bằng xác lập", icon: FileCheck2 },
];

const reviewerItems: NavigationItem[] = [
  { href: "/reviews", label: "Việc thẩm định", icon: ClipboardCheck },
  {
    href: "/work-allocations",
    label: "Công việc được giao",
    icon: ClipboardCheck,
  },
  { href: "/attendance", label: "Chấm công", icon: Clock3 },
  { href: "/leave", label: "Nghỉ phép", icon: CalendarDays },
  { href: "/overtime", label: "Tăng ca", icon: Clock3 },
];

const employeeItems: NavigationItem[] = reviewerItems.slice(2);

const adminItems: NavigationItem[] = [
  {
    href: "/admin/promotions",
    label: "Marketing & Khuyến mại",
    icon: Ticket,
    permissions: ["promotions.manage", "promotions.read"],
  },
  {
    href: "/admin/advertising",
    label: "Quản trị quảng cáo",
    icon: Megaphone,
    allowedRoles: ["SUPER_ADMIN"],
  },
  {
    href: "/admin/memberships",
    label: "Gói thành viên",
    icon: CreditCard,
    permissions: ["memberships.manage"],
  },
  {
    href: "/admin/events",
    label: "Sự kiện cộng đồng",
    icon: CalendarDays,
    permissions: ["memberships.manage"],
  },
  {
    href: "/admin/reviews",
    label: "Tiếp nhận hồ sơ",
    icon: FileText,
    permission: "review.assign",
    allowedRoles: ["SUPER_ADMIN"],
  },
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
    label: "Nhân sự",
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
    label: "Thu phí",
    icon: BadgeDollarSign,
    permission: "payments.read",
  },
  {
    href: "/admin/payments/history",
    label: "Lịch sử thanh toán",
    icon: History,
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
    href: "/admin/notifications",
    label: "Gửi thông báo",
    icon: Bell,
    allowedRoles: ["SUPER_ADMIN"],
  },
  {
    href: "/admin/content",
    label: "Nội dung công bố",
    icon: FileText,
    permission: "public_content.manage",
  },
  {
    href: "/admin/certificates",
    label: "Quản lý bằng xác lập",
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
  {
    href: "/admin/community",
    label: "Kiểm duyệt cộng đồng",
    icon: UsersRound,
    permissions: ["community.moderate", "community.manage"],
  },
];

const blockchainSignerItems: NavigationItem[] = [
  {
    href: "/admin/registry",
    label: "Ghi nhận hồ sơ",
    icon: Signature,
    permission: "blockchain.sign",
  },
];

const adminNavigationGroups = [
  { label: "Marketing & Khuyến mại", hrefs: ["/admin/promotions"] },
  {
    label: "Hồ sơ & thẩm định",
    hrefs: ["/admin/reviews", "/admin/work-allocations", "/admin/certificates"],
  },
  {
    label: "Cộng đồng & chương trình",
    hrefs: [
      "/admin/advertising",
      "/admin/memberships",
      "/admin/events",
      "/admin/community",
    ],
  },
  {
    label: "Tài chính & vận hành",
    hrefs: [
      "/admin/dashboard",
      "/admin/payments",
      "/admin/payments/history",
      "/admin/reports",
    ],
  },
  {
    label: "Nhân sự",
    hrefs: [
      "/admin/overtime",
      "/admin/leave",
      "/admin/attendance",
      "/admin/attendance/worksites",
      "/admin/payroll",
      "/admin/employees",
      "/admin/departments",
    ],
  },
  {
    label: "Nội dung & hệ thống",
    hrefs: [
      "/admin/users",
      "/admin/notifications",
      "/admin/content",
      "/admin/audit",
    ],
  },
] satisfies Array<{ label: string; hrefs: string[] }>;

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
      permissions.includes(item.permission)) &&
    (!item.permissions ||
      roles.includes("SUPER_ADMIN") ||
      item.permissions.some((permission) => permissions.includes(permission)))
  );
}

function sectionsFor(
  persona: WorkspacePersona,
  roles: readonly string[],
  permissions: readonly string[],
  isEmployee: boolean,
  area: "workspace" | "admin",
): NavigationSection[] {
  const operationalItems = adminItems.filter((item) =>
    canAccess(item, roles, permissions),
  );
  const operationalSections = adminNavigationGroups
    .map((group) => ({
      label: group.label,
      items: operationalItems.filter((item) => group.hrefs.includes(item.href)),
    }))
    .filter((section) => section.items.length > 0);
  const adminEntryPoint = resolveAdminEntryPoint(roles, permissions);
  const adminEntryItems: NavigationItem[] = adminEntryPoint
    ? [
        {
          href: adminEntryPoint.href,
          label: adminEntryPoint.label,
          icon: ShieldCheck,
        },
      ]
    : [];

  if (area === "admin") {
    return [
      {
        label: "Điều hướng",
        items: [
          {
            href: "/workspace",
            label: "Không gian cá nhân",
            icon: LayoutDashboard,
          },
          ...(roles.includes("SUPER_ADMIN")
            ? [{ href: "/admin", label: "Tổng quan quản trị", icon: Gauge }]
            : []),
          { href: "/", label: "Website", icon: House },
          { href: "/community", label: "Cộng đồng", icon: UsersRound },
          ...(roles.includes("MODERATOR")
            ? [
                {
                  href: "/reviews",
                  label: "Không gian thẩm định",
                  icon: ClipboardCheck,
                },
              ]
            : []),
          ...(roles.includes("USER")
            ? [{ href: "/dossiers", label: "Hồ sơ cá nhân", icon: FileText }]
            : []),
        ],
      },
      ...operationalSections,
      ...(canAccess(blockchainSignerItems[0]!, roles, permissions)
        ? [{ label: "Xác lập", items: blockchainSignerItems }]
        : []),
      { label: "Hỗ trợ", items: [adminSupportItem] },
    ];
  }

  if (roles.includes("MODERATOR")) {
    return [
      { label: "Thẩm định", items: reviewerItems.slice(0, 2) },
      ...(roles.includes("USER")
        ? [{ label: "Hồ sơ cá nhân", items: userItems }]
        : []),
      {
        label: "Nhân sự",
        items: isEmployee ? employeeItems : employeeItems.slice(0, 1),
      },
      { label: "Khám phá", items: discoveryItems },
      { label: "Tài chính & dịch vụ", items: personalItems.slice(0, 2) },
      {
        label: "Tài khoản",
        items: personalItems.filter((item) =>
          ["/notifications", "/account", "/activity"].includes(item.href),
        ),
      },
      ...(adminEntryItems.length
        ? [{ label: "Quản trị", items: adminEntryItems }]
        : []),
      ...(canAccess(blockchainSignerItems[0]!, roles, permissions)
        ? [{ label: "Xác lập", items: blockchainSignerItems }]
        : []),
      { label: "Hỗ trợ", items: [publicSupportItem] },
    ];
  }

  return [
    { label: "Tổng quan", items: discoveryItems.slice(0, 1) },
    ...(roles.includes("USER")
      ? [{ label: "Hồ sơ & xác lập", items: userItems }]
      : []),
    ...(roles.includes("USER") && isEmployee
      ? [{ label: "Nhân sự", items: employeeItems }]
      : []),
    {
      label: "Tài chính & dịch vụ",
      items: personalItems.filter((item) =>
        ["/vouchers", "/advertising", "/membership", "/wallet"].includes(
          item.href,
        ),
      ),
    },
    {
      label: "Tài khoản",
      items: personalItems.filter((item) =>
        ["/notifications", "/account", "/activity"].includes(item.href),
      ),
    },
    { label: "Khám phá", items: discoveryItems.slice(1) },
    ...(adminEntryItems.length
      ? [{ label: "Quản trị", items: adminEntryItems }]
      : []),
    ...(canAccess(blockchainSignerItems[0]!, roles, permissions)
      ? [{ label: "Xác lập", items: blockchainSignerItems }]
      : []),
    { label: "Hỗ trợ", items: [publicSupportItem] },
  ];
}

function isActive(pathname: string, href: string) {
  if (href === "/workspace")
    return pathname === href || pathname === "/dashboard";
  if (href === "/") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

function mobileItemsFor(
  persona: WorkspacePersona,
  items: NavigationItem[],
): NavigationItem[] {
  const operational = items.filter((item) => item.href.startsWith("/admin/"));
  const priorities: Record<WorkspacePersona, string[]> = {
    VIEWER: ["/workspace", "/works", "/community"],
    USER: ["/workspace", "/dossiers", "/community", "/wallet"],
    MODERATOR: ["/reviews", "/attendance", "/community", "/work-allocations"],
    SUPER_ADMIN: ["/workspace", "/community", "/works"],
  };
  const byHref = new globalThis.Map(items.map((item) => [item.href, item]));
  const prioritized = [
    ...priorities[persona].map((href) => byHref.get(href)),
    ...operational.filter((item) => !item.href.startsWith("/admin/")),
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
  area,
  className,
  showPrimaryNavigation = true,
  showQuickNavigation = true,
  previewRole,
  previewPathname,
  onNavigate,
  collapsedGroups,
  onToggleGroup,
}: {
  roles?: readonly string[];
  area?: "workspace" | "admin";
  className?: string;
  tone?: "light" | "dark";
  showPrimaryNavigation?: boolean;
  showQuickNavigation?: boolean;
  previewRole?: WorkspacePersona;
  previewPathname?: string;
  onNavigate?: () => void;
  onOpenMenu?: (trigger: HTMLButtonElement) => void;
  collapsedGroups?: Record<string, boolean>;
  onToggleGroup?: (label: string, collapsed: boolean) => void;
}) {
  const groupId = useId();
  const [localCollapsedGroups, setLocalCollapsedGroups] = useState<
    Record<string, boolean>
  >({});
  const groups = collapsedGroups ?? localCollapsedGroups;
  const toggleGroup =
    onToggleGroup ??
    ((label: string, collapsed: boolean) =>
      setLocalCollapsedGroups((previous) => ({
        ...previous,
        [label]: collapsed,
      })));
  const pathname = usePathname();
  const activePathname = previewRole ? (previewPathname ?? pathname) : pathname;
  const authUser = useAuthUser();
  const effectiveRoles = roles ?? authUser?.roles ?? [];
  const effectivePermissions = authUser?.permissions ?? [];
  const isEmployee = authUser?.isEmployee ?? false;
  const persona = resolveWorkspacePersona(effectiveRoles);
  const navigationArea =
    area ?? (pathname.startsWith("/admin") ? "admin" : "workspace");
  const preview = isPreviewRelease();
  const sections = [
    ...sectionsFor(
      persona,
      effectiveRoles,
      effectivePermissions,
      isEmployee,
      navigationArea,
    ),
  ].map((section) => ({
    ...section,
    items: section.items.filter(
      (item) =>
        canAccess(item, effectiveRoles, effectivePermissions) &&
        (!["/vouchers", "/wallet", "/membership"].includes(item.href) ||
          isCustomerAccount({
            roles: effectiveRoles,
            permissions: effectivePermissions,
            isEmployee,
          })) &&
        (!preview || !isPreviewRestrictedPath(item.href)),
    ),
  }));

  const allNavigationItems = sections.flatMap((section) => section.items);
  const activeHref = allNavigationItems
    .filter((item) => isActive(activePathname, item.href))
    .sort((left, right) => right.href.length - left.href.length)[0]?.href;
  const mobileItems =
    navigationArea === "admin"
      ? []
      : mobileItemsFor(persona, allNavigationItems);

  return (
    <>
      {showPrimaryNavigation ? (
        <nav
          className={cn("dashboard-navigation", className)}
          aria-label="Điều hướng"
        >
          {sections.map((section, index) => {
            const collapsed =
              groups[section.label] ??
              adminNavigationGroups.some(
                (group) => group.label === section.label,
              );
            const containsActive = section.items.some(
              (item) => item.href === activeHref,
            );
            return section.items.length ? (
              <section
                className="dashboard-navigation__section"
                key={section.label}
              >
                {navigationArea === "admin" ? (
                  <button
                    aria-label={section.label}
                    aria-controls={`${groupId}-${index}`}
                    className="dashboard-navigation__group-toggle"
                    type="button"
                    aria-expanded={!collapsed || containsActive}
                    onClick={() => toggleGroup(section.label, !collapsed)}
                  >
                    <span className="dashboard-navigation__label">
                      {section.label}
                    </span>
                    <ChevronDown aria-hidden="true" size={16} />
                  </button>
                ) : (
                  <p className="dashboard-navigation__label">{section.label}</p>
                )}
                <div
                  id={`${groupId}-${index}`}
                  className="dashboard-navigation__links"
                  hidden={
                    navigationArea === "admin" && collapsed && !containsActive
                  }
                >
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
                        title={item.label}
                        aria-label={item.label}
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
            ) : null;
          })}
        </nav>
      ) : null}

      {showQuickNavigation && navigationArea !== "admin" ? (
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
        </nav>
      ) : null}
    </>
  );
}
