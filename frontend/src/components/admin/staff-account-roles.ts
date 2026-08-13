import type { StaffAccountRole } from "@/lib/api/types";

export const STAFF_ACCOUNT_ROLES: Array<{
  value: StaffAccountRole;
  label: string;
  description: string;
}> = [
  {
    value: "REVIEWER",
    label: "Thẩm định hồ sơ",
    description: "Đọc hồ sơ được giao và gửi kết quả đánh giá.",
  },
  {
    value: "COUNCIL_MEMBER",
    label: "Thành viên Hội đồng",
    description: "Tham dự phiên, khai báo xung đột và biểu quyết.",
  },
  {
    value: "COUNCIL_SECRETARY",
    label: "Thư ký Hội đồng",
    description: "Chuẩn bị phiên họp và hoàn thiện biên bản.",
  },
  {
    value: "FINANCE_ADMIN",
    label: "Đối soát thanh toán",
    description: "Theo dõi và xử lý các khoản thanh toán nội bộ.",
  },
  {
    value: "CONTENT_ADMIN",
    label: "Biên tập nội dung",
    description: "Biên tập, duyệt và xuất bản nội dung công khai.",
  },
  {
    value: "BLOCKCHAIN_ADMIN",
    label: "Theo dõi phát hành",
    description: "Theo dõi trạng thái và đối chiếu chứng thư đã phát hành.",
  },
];

export function staffRoleLabel(role: string): string {
  return (
    STAFF_ACCOUNT_ROLES.find((item) => item.value === role)?.label ??
    "Quản trị hệ thống"
  );
}
