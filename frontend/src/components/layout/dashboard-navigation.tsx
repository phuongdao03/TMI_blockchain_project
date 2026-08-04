"use client";

import {
  BadgeCheck,
  Bell,
  BookOpenText,
  ChartNoAxesCombined,
  ChartSpline,
  ClipboardCheck,
  FileCheck2,
  FolderKanban,
  Flag,
  History,
  Landmark,
  LayoutDashboard,
  Map,
  Search,
  ScrollText,
  Settings,
  Trophy,
  Vote,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuthUser } from "@/lib/auth/user-context";
import { hasAnyRole } from "@/lib/auth/role-workspaces";
import { cn } from "@/lib/utils";

const dashboardLinks = [
  {
    href: "/dashboard",
    label: "Khám phá TMI",
    icon: LayoutDashboard,
  },
  {
    href: "/tim-kiem",
    label: "Tìm tài sản số",
    icon: Search,
  },
  {
    href: "/thu-vien",
    label: "Thư viện chứng thư",
    icon: BookOpenText,
  },
  {
    href: "/ban-do",
    label: "Bản đồ xác lập",
    icon: Map,
  },
  {
    href: "/admin/tim-kiem",
    label: "Phân tích tìm kiếm",
    icon: ChartSpline,
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/dashboard",
    label: "Tổng quan hồ sơ",
    icon: LayoutDashboard,
    roles: ["APPLICANT", "ORG_MANAGER"],
  },
  {
    href: "/ho-so",
    label: "Hồ sơ xác lập",
    icon: FolderKanban,
    roles: ["APPLICANT", "ORG_MANAGER"],
  },
  {
    href: "/chung-thu",
    label: "Chứng thư",
    icon: FileCheck2,
    roles: ["APPLICANT", "ORG_MANAGER", "SUPER_ADMIN"],
  },
  {
    href: "/tham-dinh",
    label: "Thẩm định 5T",
    icon: ClipboardCheck,
    roles: ["REVIEWER", "SUPER_ADMIN"],
  },
  {
    href: "/hoi-dong",
    label: "Hội đồng",
    icon: Landmark,
    roles: ["COUNCIL_MEMBER", "COUNCIL_SECRETARY", "SUPER_ADMIN"],
  },
  {
    href: "/admin/dashboard",
    label: "Vận hành",
    icon: ChartNoAxesCombined,
    roles: ["FINANCE_ADMIN", "BLOCKCHAIN_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/noi-dung",
    label: "Quản trị nội dung",
    icon: BookOpenText,
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/binh-chon",
    label: "Quản lý bình chọn",
    icon: Trophy,
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/bao-cao",
    label: "Báo cáo nội dung",
    icon: Flag,
    roles: ["CONTENT_ADMIN", "SUPER_ADMIN"],
  },
  {
    href: "/admin/audit",
    label: "Nhật ký audit",
    icon: ScrollText,
    roles: ["SUPER_ADMIN"],
  },
  { href: "/kiem-tra", label: "Xác minh", icon: BadgeCheck },
  { href: "/thong-bao", label: "Thông báo", icon: Bell },
  { href: "/tai-khoan", label: "Cài đặt", icon: Settings },
  { href: "/lich-su-binh-chon", label: "Lịch sử bình chọn", icon: Vote },
  { href: "/lich-su-hoat-dong", label: "Lịch sử hoạt động", icon: History },
] as const;

export function DashboardNavigation({
  className,
  tone = "dark",
}: {
  className?: string;
  tone?: "dark" | "light";
}) {
  const pathname = usePathname();
  const user = useAuthUser();
  const activeClass =
    tone === "dark"
      ? "bg-white text-ink-950 shadow-lg shadow-black/10"
      : "bg-primary-50 text-primary-700";
  const linkClass =
    tone === "dark"
      ? "text-slate-300 hover:bg-white/5 hover:text-white"
      : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-950";

  return (
    <div className={cn("grid gap-1.5", className)}>
      {dashboardLinks
        .filter(
          (item) =>
            !("roles" in item) || hasAnyRole(user?.roles ?? [], item.roles),
        )
        .map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" &&
              Boolean(pathname?.startsWith(item.href)));
          return (
            <Link
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex min-h-12 items-center gap-3 rounded-xl px-3.5 text-sm font-bold transition-colors",
                isActive ? activeClass : linkClass,
              )}
              href={item.href}
              key={item.href}
            >
              <Icon aria-hidden="true" className="size-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
    </div>
  );
}
