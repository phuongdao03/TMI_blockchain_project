const withdrawalStatusLabels: Record<string, string> = {
  PENDING_REVIEW: "Chờ xét duyệt",
  APPROVED: "Đã duyệt · chờ chi trả",
  REJECTED: "Đã từ chối",
  CANCELLED: "Đã hủy",
  QUEUED: "Đang chờ chi trả",
  PROCESSING: "Đang xử lý chi trả",
  RECONCILIATION_REQUIRED: "Cần kiểm tra giao dịch",
  SUCCEEDED: "Đã hoàn tất",
  FAILED: "Không thành công",
  UNKNOWN: "Chưa xác định",
};

const payoutAttemptStatusLabels: Record<string, string> = {
  CREATED: "Đã tạo lệnh",
  SENDING: "Đang gửi lệnh",
  PROCESSING: "Đang xử lý",
  SUCCEEDED: "Đã hoàn tất",
  FAILED: "Không thành công",
  UNKNOWN: "Chưa xác định",
};

const bankVerificationStatusLabels: Record<string, string> = {
  UNVERIFIED: "Chưa xác minh",
  VERIFIED: "Đã xác minh",
  REJECTED: "Không đạt yêu cầu",
};

export function withdrawalStatusLabel(status: string) {
  return withdrawalStatusLabels[status] ?? "Trạng thái chưa xác định";
}

export function payoutAttemptStatusLabel(status: string) {
  return payoutAttemptStatusLabels[status] ?? "Trạng thái chưa xác định";
}

export function bankVerificationStatusLabel(status: string) {
  return bankVerificationStatusLabels[status] ?? "Chưa xác minh";
}

export function identityVerificationStatusLabel(status: string) {
  return status === "VERIFIED" ? "Đã xác minh" : "Không đạt yêu cầu";
}
