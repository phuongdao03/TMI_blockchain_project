import type { AuditLogItem } from "@/lib/api/types";

const exactActionLabels: Record<string, string> = {
  "audit.read": "Đã mở lịch sử vận hành",
  "audit.exported": "Đã tải báo cáo lịch sử",
  "audit.integrity_checked": "Đã kiểm tra tính toàn vẹn bản ghi",
  "certificate.version.approved": "Đã phê duyệt chứng thư",
  "certificate.version.rejected": "Đã từ chối chứng thư",
  "dossier.approved": "Đã phê duyệt hồ sơ",
  "payment.confirmed": "Đã xác nhận thanh toán",
  "blockchain.transaction.confirmed": "Đã xác nhận giao dịch blockchain",
  "blockchain.transaction.failed": "Giao dịch blockchain chưa thành công",
  "admin.staff_account.updated": "Đã cập nhật tài khoản nhân sự",
  "admin.staff_permissions.replaced": "Đã cập nhật quyền nhân sự",
  "admin.staff_invitation.created": "Đã gửi lời mời",
  "admin.staff_invitation.resent": "Đã gửi lại lời mời nhân sự",
  "admin.staff_invitation.revoked": "Đã thu hồi lời mời nhân sự",
  "auth.staff_invitation.accepted": "Nhân sự đã chấp nhận lời mời",
  "admin.privileged_action.requested": "Đã gửi yêu cầu thay đổi đặc quyền",
  "admin.privileged_action.approved": "Đã phê duyệt thay đổi đặc quyền",
  "cms.post.created": "Đã tạo bài viết",
  "cms.post.updated": "Đã cập nhật bài viết",
  "cms.post.published": "Đã xuất bản bài viết",
  "cms.page.created": "Đã tạo trang nội dung",
  "cms.page.updated": "Đã cập nhật trang nội dung",
  "cms.page.published": "Đã xuất bản trang nội dung",
  "cms.banner.created": "Đã tạo banner",
  "cms.banner.updated": "Đã cập nhật banner",
  "cms.banner.published": "Đã xuất bản banner",
  "cms.category.created": "Đã tạo danh mục",
  "cms.category.updated": "Đã cập nhật danh mục",
  "cms.category.deleted": "Đã xóa danh mục",
  "blockchain.wallet.linked": "Đã liên kết ví ký blockchain",
  "blockchain.wallet.revoked": "Đã thu hồi ví ký blockchain",
  "blockchain.signature.requested": "Đã tạo yêu cầu ký blockchain",
  "blockchain.transaction.submitted": "Đã gửi giao dịch blockchain",
};

const actionLabels: Record<string, string> = {
  created: "Đã tạo mới",
  updated: "Đã cập nhật",
  approved: "Đã phê duyệt",
  rejected: "Đã từ chối",
  requested: "Đã gửi yêu cầu",
  confirmed: "Đã xác nhận",
  published: "Đã phát hành",
  revoked: "Đã thu hồi",
  read: "Đã xem",
  exported: "Đã tải báo cáo",
  integrity_checked: "Đã kiểm tra tính toàn vẹn",
};

const resourceLabels: Record<string, string> = {
  audit_log: "Lịch sử vận hành",
  blockchain_transaction: "Giao dịch blockchain",
  certificate: "Chứng thư",
  certificate_version: "Phiên bản chứng thư",
  dossier: "Hồ sơ",
  document: "Tài liệu",
  payment: "Thanh toán",
  transaction: "Giao dịch xác nhận",
  user: "Tài khoản",
  staff_account: "Tài khoản nhân sự",
  staff_invitation: "Lời mời nhân sự",
  privileged_action: "Yêu cầu đặc quyền",
  post: "Bài viết",
  page: "Trang nội dung",
  banner: "Banner",
  category: "Danh mục",
  blockchain_wallet_link: "Ví ký blockchain",
  cms_post: "Bài viết",
  cms_page: "Trang nội dung",
  cms_banner: "Banner",
  cms_category: "Danh mục",
};

const roleLabels: Record<string, string> = {
  MODERATOR: "Người kiểm duyệt",
  SUPER_ADMIN: "Quản trị hệ thống",
  USER: "Người nộp hồ sơ",
  VIEWER: "Người tra cứu",
};

function stringValue(
  record: Record<string, unknown> | null,
  key: string,
): string | null {
  const value = record?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

const serviceLabels: Record<string, string> = {
  "blockchain-worker": "Hệ thống blockchain",
  "certificate-worker": "Hệ thống cấp chứng thư",
  "payment-worker": "Hệ thống thanh toán",
  "notification-worker": "Hệ thống thông báo",
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
  const normalized = action.toLowerCase();
  if (exactActionLabels[normalized]) return exactActionLabels[normalized];
  const suffix = normalized.split(".").at(-1) ?? action;
  return actionLabels[suffix] ?? "Đã ghi nhận thay đổi";
}

export function resourceLabel(resource: string): string {
  return resourceLabels[resource.toLowerCase()] ?? "Nội dung nghiệp vụ";
}

export function actorLabel(
  actorType: AuditLogItem["actorType"],
  actorService?: string | null,
): string {
  if (actorType === "USER") return "Quản trị viên nội bộ";
  if (actorType === "SERVICE") {
    return actorService
      ? (serviceLabels[actorService.toLowerCase()] ?? "Tác vụ hệ thống")
      : "Tác vụ hệ thống";
  }
  return "Phiên không định danh";
}

export function auditEventSummary(row: AuditLogItem): string {
  if (row.action === "admin.user.status_changed") {
    const status = stringValue(row.after, "status");
    if (status === "SUSPENDED") return "Đã khóa tài khoản";
    if (status === "DISABLED") return "Đã vô hiệu hóa tài khoản";
    if (status === "ACTIVE") return "Đã kích hoạt tài khoản";
    return "Đã thay đổi trạng thái tài khoản";
  }
  if (row.action === "admin.staff_invitation.created") {
    const role = stringValue(row.after, "role");
    return role
      ? `Đã gửi lời mời ${roleLabels[role] ?? role}`
      : "Đã gửi lời mời nhân sự";
  }
  if (row.action === "admin.staff_account.updated") {
    const beforeStatus = stringValue(row.before, "status");
    const afterStatus = stringValue(row.after, "status");
    if (beforeStatus !== afterStatus && afterStatus === "SUSPENDED") {
      return "Đã khóa tài khoản nhân sự";
    }
    if (beforeStatus !== afterStatus && afterStatus === "ACTIVE") {
      return "Đã mở lại tài khoản nhân sự";
    }
  }
  const action = actionLabel(row.action);
  if (exactActionLabels[row.action.toLowerCase()]) return action;
  const resource = resourceLabel(row.resourceType).toLocaleLowerCase("vi");
  const actionAlreadyNamesResource =
    row.action.startsWith("audit.") ||
    row.action.startsWith("certificate.version.") ||
    row.action.startsWith("blockchain.transaction.") ||
    row.action === "dossier.approved" ||
    row.action === "payment.confirmed";

  return actionAlreadyNamesResource ? action : `${action} ${resource}`;
}

export function formatAuditTimestamp(value: string): {
  date: string;
  time: string;
} {
  const date = new Date(value);
  return {
    date: new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date),
    time: new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(date),
  };
}
