"use client";

import {
  Bell,
  BookOpen,
  FileCheck2,
  FileText,
  Gauge,
  History,
  LayoutDashboard,
  Map,
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
import { isPreviewRelease, isPreviewRestrictedPath } from "@/lib/release-mode";

type NavigationItem = {
  href: string;
  label: string;
  icon: typeof Gauge;
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

const userItems: NavigationItem[] = [
  { href: "/dossiers", label: "Hồ sơ của tôi", icon: FileText },
  { href: "/certificates", label: "Chứng thư", icon: FileCheck2 },
];

const reviewerItems: NavigationItem[] = [
  { href: "/reviews", label: "Hồ sơ đánh giá", icon: FileCheck2 },
  {
    href: "/reviews/similarity",
    label: "Đối chiếu nội dung",
    icon: Search,
  },
  { href: "/council", label: "Phiên xét duyệt", icon: FileCheck2 },
];

const adminItems: NavigationItem[] = [
  {
    href: "/admin/dashboard",
    label: "Tổng quan vận hành",
    icon: Gauge,
  },
  { href: "/admin/staff", label: "Tài khoản nhân sự", icon: UsersRound },
  { href: "/admin/content", label: "Nội dung công bố", icon: FileText },
  { href: "/admin/audit", label: "Lịch sử hoạt động", icon: History },
  { href: "/admin/reports", label: "Báo cáo", icon: FileCheck2 },
];

const blockchainSignerItems: NavigationItem[] = [
  { href: "/blockchain", label: "Ký blockchain", icon: Signature },
];

function sectionsFor(persona: WorkspacePersona): NavigationSection[] {
  if (persona === "SUPER_ADMIN") {
    return [
      { label: "Điều hành", items: adminItems },
      { label: "Tra cứu", items: discoveryItems.slice(1) },
      { label: "Cá nhân", items: personalItems.slice(0, 2) },
    ];
  }

  if (persona === "MODERATOR") {
    return [
      { label: "Công việc", items: reviewerItems },
      { label: "Tra cứu", items: discoveryItems.slice(1) },
      { label: "Cá nhân", items: personalItems.slice(0, 2) },
    ];
  }

  return [
    { label: "Khám phá", items: discoveryItems },
    ...(persona === "USER" ? [{ label: "Hồ sơ", items: userItems }] : []),
    { label: "Cá nhân", items: personalItems },
  ];
}

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function DashboardNavigation({
  roles,
  className,
}: {
  roles?: readonly string[];
  className?: string;
  tone?: "light" | "dark";
}) {
  const pathname = usePathname();
  const authUser = useAuthUser();
  const effectiveRoles = roles ?? authUser?.roles ?? [];
  const persona = resolveWorkspacePersona(effectiveRoles);
  const preview = isPreviewRelease();
  const sections = [
    ...sectionsFor(persona),
    ...(effectiveRoles.includes("SUPER_ADMIN")
      ? [{ label: "Blockchain", items: blockchainSignerItems }]
      : []),
  ].map((section) => ({
    ...section,
    items: section.items.filter(
      (item) => !preview || !isPreviewRestrictedPath(item.href),
    ),
  }));

  const mobileItems = sections.flatMap((section) => section.items).slice(0, 5);

  return (
    <>
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
                    >
                      <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </section>
          ) : null,
        )}
      </nav>

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
            >
              <Icon aria-hidden="true" size={21} strokeWidth={1.8} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
