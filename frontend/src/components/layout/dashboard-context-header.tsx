"use client";

import { Bell, ChevronRight, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { LogoutButton } from "@/components/auth/logout-button";
import { BrandMark } from "@/components/layout/brand-mark";
import { useAuthUser } from "@/lib/auth/user-context";

const sections = [
  { prefix: "/activity", label: "Lịch sử hoạt động" },
  { prefix: "/vote-history", label: "Lịch sử bình chọn" },
  { prefix: "/admin/voting", label: "Quản lý bình chọn" },
  { prefix: "/admin/reports", label: "Báo cáo nội dung" },
  { prefix: "/admin/content", label: "Quản trị nội dung" },
  { prefix: "/admin/dashboard", label: "Điều hành hệ thống" },
  { prefix: "/admin/audit", label: "Lịch sử thay đổi" },
  { prefix: "/notifications", label: "Thông báo" },
  { prefix: "/council/", label: "Chi tiết phiên Hội đồng" },
  { prefix: "/council", label: "Phiên xét duyệt Hội đồng" },
  { prefix: "/reviews/", label: "Chi tiết thẩm định" },
  { prefix: "/reviews", label: "Hàng đợi thẩm định" },
  { prefix: "/dossiers/new", label: "Tạo hồ sơ" },
  { prefix: "/dossiers/", label: "Chi tiết hồ sơ" },
  { prefix: "/dossiers", label: "Hồ sơ xác lập" },
  { prefix: "/certificates", label: "Chứng thư số" },
  { prefix: "/account", label: "Tài khoản và tổ chức" },
  { prefix: "/dashboard", label: "Tổng quan" },
] as const;

export function DashboardContextHeader() {
  const pathname = usePathname() ?? "/dashboard";
  const user = useAuthUser();
  const label =
    sections.find(({ prefix }) => pathname.startsWith(prefix))?.label ??
    "Không gian làm việc";

  return (
    <div className="flex min-h-18 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 xl:px-10">
      <BrandMark className="lg:hidden" />
      <div className="hidden items-center gap-2 text-sm lg:flex">
        <span className="font-medium text-neutral-400">TMI Certificate</span>
        <ChevronRight aria-hidden="true" className="size-4 text-neutral-300" />
        <span className="font-bold text-neutral-900">{label}</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <span className="hidden max-w-56 items-center gap-2 rounded-full border border-neutral-200 bg-[#f7f4ee] px-3 py-1.5 text-xs font-semibold text-neutral-600 sm:inline-flex">
          <UserRound
            aria-hidden="true"
            className="size-3.5 shrink-0 text-primary-700"
          />
          <span className="truncate">{user?.email ?? "Tài khoản của bạn"}</span>
        </span>
        <Link
          aria-label="Thông báo"
          className="grid size-11 place-items-center rounded-xl border border-neutral-200 bg-white text-neutral-600 hover:border-primary-200 hover:text-primary-700"
          href="/notifications"
        >
          <Bell aria-hidden="true" className="size-4.5" />
        </Link>
        <LogoutButton />
      </div>
    </div>
  );
}
