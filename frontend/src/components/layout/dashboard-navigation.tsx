"use client";

import {
  ArrowLeftRight,
  BadgeCheck,
  Bell,
  BookOpenText,
  ChartNoAxesCombined,
  ChartSpline,
  ClipboardCheck,
  FileCheck2,
  FileClock,
  FolderKanban,
  Flag,
  History,
  Landmark,
  LayoutDashboard,
  Map,
  Search,
  ScrollText,
  Settings,
  ShieldCheck,
  Trophy,
  Vote,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuthUser } from "@/lib/auth/user-context";
import {
  hasAnyRole,
  resolveWorkspacePersona,
  type WorkspacePersona,
} from "@/lib/auth/role-workspaces";
import { cn } from "@/lib/utils";

interface DashboardLink {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  section: "work" | "explore" | "manage" | "account";
  personas?: readonly WorkspacePersona[];
  roles?: readonly string[];
}

const dashboardLinks: readonly DashboardLink[] = [
  {
    href: "/dashboard",
    label: "Khám phá TMI",
    icon: LayoutDashboard,
    section: "explore",
    personas: ["PUBLIC"],
  },
  {
    href: "/search",
    label: "Tìm tài sản số",
    icon: Search,
    section: "explore",
    personas: ["PUBLIC", "APPLICANT"],
  },
  {
    href: "/works",
    label: "Thư viện chứng thư",
    icon: BookOpenText,
    section: "explore",
    personas: ["PUBLIC", "APPLICANT"],
  },
  {
    href: "/map",
    label: "Bản đồ xác lập",
    icon: Map,
    section: "explore",
    personas: ["PUBLIC"],
  },
  {
    href: "/admin/search",
    label: "Phân tích tìm kiếm",
    icon: ChartSpline,
    section: "manage",
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/dashboard",
    label: "Việc cần làm",
    icon: LayoutDashboard,
    section: "work",
    roles: ["APPLICANT", "ORG_MANAGER"],
  },
  {
    href: "/dossiers",
    label: "Hồ sơ của tôi",
    icon: FolderKanban,
    section: "work",
    roles: ["APPLICANT", "ORG_MANAGER"],
  },
  {
    href: "/certificates",
    label: "Chứng thư",
    icon: FileCheck2,
    section: "work",
    roles: ["APPLICANT", "ORG_MANAGER", "SUPER_ADMIN"],
  },
  {
    href: "/reviews",
    label: "Hồ sơ cần đánh giá",
    icon: ClipboardCheck,
    section: "work",
    roles: ["REVIEWER", "SUPER_ADMIN"],
  },
  {
    href: "/reviews/similarity",
    label: "Đối chiếu tương đồng",
    icon: ArrowLeftRight,
    section: "work",
    roles: ["REVIEWER"],
  },
  {
    href: "/council",
    label: "Hội đồng",
    icon: Landmark,
    section: "work",
    roles: ["COUNCIL_MEMBER", "COUNCIL_SECRETARY", "SUPER_ADMIN"],
  },
  {
    href: "/admin",
    label: "Trung tâm quản trị",
    icon: ShieldCheck,
    section: "manage",
    roles: ["SUPER_ADMIN"],
  },
  {
    href: "/admin/similarity",
    label: "Phân công đối chiếu",
    icon: ArrowLeftRight,
    section: "manage",
    roles: ["SUPER_ADMIN"],
  },
  {
    href: "/admin/certificate-updates",
    label: "Cập nhật chứng thư",
    icon: FileClock,
    section: "manage",
    roles: ["SUPER_ADMIN"],
  },
  {
    href: "/admin/dashboard",
    label: "Vận hành",
    icon: ChartNoAxesCombined,
    section: "manage",
    roles: ["FINANCE_ADMIN", "BLOCKCHAIN_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/content",
    label: "Quản trị nội dung",
    icon: BookOpenText,
    section: "manage",
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/voting",
    label: "Quản lý bình chọn",
    icon: Trophy,
    section: "manage",
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/reports",
    label: "Báo cáo nội dung",
    icon: Flag,
    section: "manage",
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/audit",
    label: "Lịch sử thay đổi",
    icon: ScrollText,
    section: "manage",
    roles: ["SUPER_ADMIN"],
  },
  {
    href: "/verify",
    label: "Tra cứu chứng thư",
    icon: BadgeCheck,
    section: "explore",
    personas: ["PUBLIC", "APPLICANT"],
  },
  {
    href: "/notifications",
    label: "Thông báo",
    icon: Bell,
    section: "account",
  },
  { href: "/account", label: "Tài khoản", icon: Settings, section: "account" },
  {
    href: "/vote-history",
    label: "Bình chọn của tôi",
    icon: Vote,
    section: "account",
    personas: ["PUBLIC", "APPLICANT"],
  },
  {
    href: "/activity",
    label: "Hoạt động gần đây",
    icon: History,
    section: "account",
  },
];

const sectionLabels = {
  work: "Việc cần làm",
  explore: "Tra cứu",
  manage: "Điều hành",
  account: "Cá nhân",
} as const;

export function DashboardNavigation({
  className,
  tone = "dark",
}: {
  className?: string;
  tone?: "dark" | "light";
}) {
  const pathname = usePathname();
  const user = useAuthUser();
  const persona = resolveWorkspacePersona(user?.roles ?? []);
  const activeClass =
    tone === "dark"
      ? "bg-white text-ink-950 shadow-lg shadow-black/10"
      : "bg-primary-50 text-primary-700";
  const linkClass =
    tone === "dark"
      ? "text-slate-300 hover:bg-white/5 hover:text-white"
      : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-950";
  const visibleLinks = dashboardLinks.filter((item) => {
    if (item.roles && !hasAnyRole(user?.roles ?? [], item.roles)) return false;
    if (item.personas && !item.personas.includes(persona)) return false;
    return true;
  });
  const activeHref = visibleLinks
    .filter(
      (item) =>
        pathname === item.href ||
        (item.href !== "/dashboard" &&
          Boolean(pathname?.startsWith(`${item.href}/`))),
    )
    .sort((left, right) => right.href.length - left.href.length)[0]?.href;

  const sections = (["work", "manage", "explore", "account"] as const)
    .map((key) => ({
      key,
      items: visibleLinks.filter((item) => item.section === key),
    }))
    .filter(({ items }) => items.length > 0);

  return (
    <div className={cn("grid gap-6", className)}>
      {sections.map(({ key, items }) => (
        <section key={key}>
          <p className="mb-2 px-3 text-[0.62rem] font-bold uppercase tracking-[0.18em] text-slate-500">
            {sectionLabels[key]}
          </p>
          <div className="grid gap-1">
            {items.map((item) => {
              const Icon = item.icon;
              const isActive = activeHref === item.href;
              return (
                <Link
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "group flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold transition-colors",
                    isActive ? activeClass : linkClass,
                  )}
                  href={item.href}
                  key={`${item.href}-${item.label}`}
                >
                  <Icon aria-hidden="true" className="size-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
