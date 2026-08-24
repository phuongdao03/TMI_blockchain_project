import type { StaffAccountRole } from "@/lib/api/types";

export const STAFF_ACCOUNT_ROLES: Array<{
  value: StaffAccountRole;
  label: string;
  description: string;
}> = [
  {
    value: "MODERATOR",
    label: "Người kiểm duyệt",
    description: "Kiểm tra hồ sơ, thẩm định bằng chứng và hoàn tất quyết định.",
  },
];

export function staffRoleLabel(role: string): string {
  return (
    STAFF_ACCOUNT_ROLES.find((item) => item.value === role)?.label ??
    "Quản trị hệ thống"
  );
}
