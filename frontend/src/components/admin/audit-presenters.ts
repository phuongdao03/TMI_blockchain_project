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
  "auth.staff_invitation.declined": "Người dùng đã từ chối lời mời kiểm duyệt",
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
  "public.verification.completed": "Đã kiểm tra chứng thư công khai",
  "public_work.published": "Đã công bố tác phẩm",
  "public_work.media_attached": "Đã thêm nội dung công khai",
  "certificate.issued": "Đã cấp chứng thư",
  "hr.department.created": "Đã tạo phòng ban",
  "hr.department.updated": "Đã cập nhật phòng ban",
  "hr.employee.created": "Đã tạo hồ sơ nhân viên",
  "hr.employee.updated": "Đã cập nhật hồ sơ nhân viên",
  "hr.attendance_worksite.created": "Đã tạo điểm làm việc",
  "hr.attendance_worksite.updated": "Đã cập nhật điểm làm việc",
  "hr.attendance_worksite_policy.created": "Đã lưu chính sách chấm công",
  "hr.attendance_assignment.created": "Đã phân công điểm chấm công",
  "hr.attendance.checked_in": "Nhân viên đã chấm công vào",
  "hr.attendance.checked_out": "Nhân viên đã chấm công ra",
  "hr.attendance.adjusted": "Đã điều chỉnh chấm công",
  "hr.attendance_location_exception.decided": "Đã xử lý ngoại lệ vị trí",
  "hr.leave.created": "Đã gửi yêu cầu nghỉ phép",
  "hr.leave.cancelled": "Đã hủy yêu cầu nghỉ phép",
  "hr.overtime.created": "Đã gửi yêu cầu tăng ca",
  "hr.overtime.cancelled": "Đã hủy yêu cầu tăng ca",
  "hr.payroll.created": "Đã tạo kỳ lương",
  "hr.payroll.calculated": "Đã tính bảng lương",
  "hr.payroll.entry_adjusted": "Đã điều chỉnh khoản lương",
  "hr.payroll.confirmed": "Đã xác nhận bảng lương",
  "hr.payroll.paid": "Đã ghi nhận trả lương",
  "work.task.created": "Đã tạo công việc",
  "work.task.updated": "Đã cập nhật công việc",
  "work.task.checklist.created": "Đã thêm mục kiểm tra công việc",
  "work.task.comment.created": "Đã bình luận công việc",
  "work.task.attachment.added": "Đã đính kèm tệp công việc",
  "work.allocation.created": "Đã tạo phân công công việc",
  "work.allocation.activated": "Đã kích hoạt phân công công việc",
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
  certificate_verification: "Tra cứu chứng thư",
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
  public_work: "Tác phẩm công khai",
  public_category: "Danh mục công khai",
  public_tag: "Nhãn công khai",
  department: "Phòng ban",
  employee: "Nhân viên",
  attendance_worksite: "Điểm làm việc",
  attendance_worksite_policy: "Chính sách chấm công",
  attendance_assignment: "Phân công chấm công",
  attendance: "Chấm công",
  attendance_location_exception: "Ngoại lệ vị trí",
  leave_request: "Nghỉ phép",
  overtime_request: "Tăng ca",
  payroll_period: "Kỳ lương",
  payroll_entry: "Khoản lương",
  task: "Công việc",
  work_allocation: "Phân công công việc",
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
  "certificate-issuance-worker": "Hệ thống cấp chứng thư",
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

const outcomeLabels: Record<string, { label: string; className: string }> = {
  VALID: {
    label: "Hợp lệ",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  CONFIRMED: {
    label: "Đã xác nhận",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  PUBLISHED: {
    label: "Đã công bố",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  FAILED: {
    label: "Chưa thành công",
    className: "border-red-200 bg-red-50 text-red-800",
  },
  REJECTED: {
    label: "Đã từ chối",
    className: "border-red-200 bg-red-50 text-red-800",
  },
  REVOKED: {
    label: "Đã thu hồi",
    className: "border-amber-200 bg-amber-50 text-amber-800",
  },
};

export function auditOutcome(row: AuditLogItem): {
  label: string;
  className: string;
} {
  const status = (
    stringValue(row.after, "status") ??
    stringValue(row.after, "publication_status")
  )?.toUpperCase();
  if (status && outcomeLabels[status]) return outcomeLabels[status];
  if (row.action.endsWith(".published")) return outcomeLabels.PUBLISHED!;
  if (row.action.endsWith(".rejected")) return outcomeLabels.REJECTED!;
  if (row.action.endsWith(".failed")) return outcomeLabels.FAILED!;
  return integrityLabels[row.integrityStatus];
}

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
  return "Người dùng chưa xác định";
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

export function auditTargetLabel(row: AuditLogItem): string {
  const value =
    stringValue(row.after, "certificate_number") ??
    stringValue(row.after, "dossier_code") ??
    stringValue(row.after, "title") ??
    stringValue(row.after, "name") ??
    stringValue(row.after, "employee_code") ??
    stringValue(row.after, "code") ??
    stringValue(row.before, "certificate_number") ??
    stringValue(row.before, "dossier_code") ??
    stringValue(row.before, "title") ??
    stringValue(row.before, "name") ??
    stringValue(row.before, "employee_code") ??
    stringValue(row.before, "code");
  return value
    ? `${resourceLabel(row.resourceType)} · ${value}`
    : resourceLabel(row.resourceType);
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
