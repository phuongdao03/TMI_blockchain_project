import type { AuditLogItem } from "@/lib/api/types";

const actionLabels: Record<string, string> = {
  created: "Đã tạo mới",
  updated: "Đã cập nhật",
  approved: "Đã phê duyệt",
  rejected: "Đã từ chối",
  requested: "Đã gửi yêu cầu",
  confirmed: "Đã xác nhận",
  published: "Đã phát hành",
  revoked: "Đã thu hồi",
  read: "Đã xem lịch sử",
  exported: "Đã tải báo cáo",
  integrity_checked: "Đã kiểm tra tính toàn vẹn",
};

const resourceLabels: Record<string, string> = {
  audit_log: "Lịch sử vận hành",
  certificate: "Chứng thư",
  certificate_version: "Phiên bản chứng thư",
  dossier: "Hồ sơ",
  document: "Tài liệu",
  payment: "Thanh toán",
  transaction: "Giao dịch xác nhận",
  user: "Tài khoản nhân sự",
};

export const integrityLabels: Record<
  AuditLogItem["integrityStatus"],
  { label: string; className: string }
> = {
  VERIFIED: {
    label: "Đã kiểm chứng",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  TAMPERED: {
    label: "Cần kiểm tra",
    className: "border-red-200 bg-red-50 text-red-800",
  },
  UNSEALED: {
    label: "Bản ghi cũ",
    className: "border-amber-200 bg-amber-50 text-amber-800",
  },
  KEY_UNAVAILABLE: {
    label: "Chưa thể đối chiếu",
    className: "border-neutral-300 bg-neutral-100 text-neutral-700",
  },
};

export function actionLabel(action: string): string {
  const parts = action.toLowerCase().split(".");
  const suffix = parts.at(-1) ?? action;
  return actionLabels[suffix] ?? "Đã ghi nhận thay đổi";
}

export function resourceLabel(resource: string): string {
  return resourceLabels[resource.toLowerCase()] ?? "Nội dung nghiệp vụ";
}

export function actorLabel(actorType: AuditLogItem["actorType"]): string {
  if (actorType === "USER") return "Nhân sự nội bộ";
  if (actorType === "SERVICE") return "Tác vụ tự động";
  return "Phiên không định danh";
}
