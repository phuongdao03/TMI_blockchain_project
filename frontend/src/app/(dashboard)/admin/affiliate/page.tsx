import type { Metadata } from "next";

import { AdminAffiliateWorkspace } from "@/components/admin/admin-affiliate-workspace";

export const metadata: Metadata = {
  title: "Quản trị tiếp thị liên kết",
  description: "Quản lý hồ sơ giới thiệu, hoa hồng và chính sách chi trả.",
};

export default function AdminAffiliatePage() {
  return <AdminAffiliateWorkspace />;
}
