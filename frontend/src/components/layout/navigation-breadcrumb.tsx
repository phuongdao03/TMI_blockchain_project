"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const parents: Record<string, string> = {
  "/works": "Khám phá đề cử",
  "/community": "Cộng đồng",
  "/dossiers": "Hồ sơ của tôi",
  "/reviews": "Thẩm định",
  "/work-allocations": "Công việc",
  "/certificates": "Bằng xác lập",
  "/admin/reviews": "Tiếp nhận hồ sơ",
  "/admin/work-allocations": "Phân công công việc",
  "/admin/attendance": "Chấm công",
  "/admin/payments": "Thanh toán",
  "/admin": "Quản trị",
};
const pageLabels: Record<string, string> = {
  new: "Tạo mới",
  edit: "Chỉnh sửa",
  mine: "Bài viết của tôi",
  history: "Lịch sử",
  worksites: "Địa điểm chấm công",
  users: "Tài khoản",
  employees: "Nhân sự",
  departments: "Phòng ban",
  promotions: "Marketing & Khuyến mại",
  memberships: "Gói thành viên",
  advertising: "Quảng cáo",
  dashboard: "Tổng quan vận hành",
  content: "Nội dung",
  notifications: "Thông báo",
  audit: "Lịch sử hoạt động",
  reports: "Báo cáo",
  registry: "Ghi nhận hồ sơ",
  leave: "Nghỉ phép",
  overtime: "Tăng ca",
  payroll: "Bảng lương",
  events: "Sự kiện",
  guide: "Hướng dẫn",
};

export function NavigationBreadcrumb() {
  const path = usePathname();
  const parent = Object.keys(parents)
    .filter((href) => path.startsWith(`${href}/`))
    .sort((a, b) => b.length - a.length)[0];
  if (!parent) return null;
  const label =
    pageLabels[path.split("/").at(-1) ?? ""] ??
    (parent === "/works"
      ? "Chi tiết đề cử"
      : parent === "/dossiers"
        ? "Chi tiết hồ sơ"
        : parent === "/reviews"
          ? "Hồ sơ thẩm định"
          : "Chi tiết");
  return (
    <nav className="navigation-breadcrumb" aria-label="Đường dẫn">
      <Link href={parent}>{parents[parent]}</Link>
      <span aria-hidden="true">/</span>
      <span aria-current="page">{label}</span>
    </nav>
  );
}
