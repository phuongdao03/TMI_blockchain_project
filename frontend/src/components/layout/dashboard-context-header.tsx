"use client";

import { Bell, ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { BrandMark } from "@/components/layout/brand-mark";

const sections = [
  { prefix: "/lich-su-hoat-dong", label: "Lịch sử hoạt động" },
  { prefix: "/lich-su-binh-chon", label: "Lịch sử bình chọn" },
  { prefix: "/admin/binh-chon", label: "Quản lý bình chọn" },
  { prefix: "/admin/bao-cao", label: "Báo cáo nội dung" },
  { prefix: "/admin/noi-dung", label: "Quản trị nội dung" },
  { prefix: "/admin/dashboard", label: "Điều hành hệ thống" },
  { prefix: "/admin/audit", label: "Nhật ký kiểm toán" },
  { prefix: "/thong-bao", label: "Thông báo" },
  { prefix: "/hoi-dong/", label: "Chi tiết phiên Hội đồng" },
  { prefix: "/hoi-dong", label: "Phiên xét duyệt Hội đồng" },
  { prefix: "/tham-dinh/", label: "Chi tiết thẩm định" },
  { prefix: "/tham-dinh", label: "Hàng đợi thẩm định" },
  { prefix: "/ho-so/tao-moi", label: "Tạo hồ sơ" },
  { prefix: "/ho-so/", label: "Chi tiết hồ sơ" },
  { prefix: "/ho-so", label: "Hồ sơ xác lập" },
  { prefix: "/chung-thu", label: "Chứng thư số" },
  { prefix: "/tai-khoan", label: "Tài khoản và tổ chức" },
  { prefix: "/dashboard", label: "Tổng quan" },
] as const;

export function DashboardContextHeader() {
  const pathname = usePathname() ?? "/dashboard";
  const label =
    sections.find(({ prefix }) => pathname.startsWith(prefix))?.label ??
    "Không gian làm việc";

  return (
    <div className="flex min-h-18 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 xl:px-10">
      <BrandMark className="lg:hidden [&>span:first-child]:size-11 [&>span:first-child>img]:size-11 [&>span:last-child]:hidden sm:[&>span:last-child]:block" />
      <div className="hidden items-center gap-2 text-sm lg:flex">
        <span className="font-medium text-neutral-400">TMI Certificate</span>
        <ChevronRight aria-hidden="true" className="size-4 text-neutral-300" />
        <span className="font-bold text-neutral-900">{label}</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <span className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800 sm:inline-flex">
          <span className="size-1.5 rounded-full bg-emerald-500" />
          Hệ thống hoạt động
        </span>
        <Link
          aria-label="Thông báo"
          className="grid size-11 place-items-center rounded-xl border border-neutral-200 bg-white text-neutral-600 hover:border-primary-200 hover:text-primary-700"
          href="/thong-bao"
        >
          <Bell aria-hidden="true" className="size-4.5" />
        </Link>
      </div>
    </div>
  );
}
