const profileStatusLabels: Record<string, string> = {
  ACTIVE: "Đang hoạt động",
  SUSPENDED: "Tạm ngưng",
};

const commissionStatusLabels: Record<string, string> = {
  PENDING: "Chờ duyệt",
  ON_HOLD: "Đang tạm giữ",
  APPROVED: "Đã phê duyệt",
  AVAILABLE: "Có thể rút",
  REJECTED: "Đã từ chối",
  REVERSED: "Đã thu hồi",
  SUPPRESSED: "Không đủ điều kiện",
  SETTLED: "Đã thanh toán",
};

const ruleStatusLabels: Record<string, string> = {
  DRAFT: "Bản nháp",
  PUBLISHED: "Đã phát hành",
};

const serviceLabels: Record<string, string> = {
  DOSSIER_SUBMISSION: "Nộp hồ sơ",
  MEMBERSHIP: "Gói thành viên",
  ADVERTISING: "Dịch vụ quảng cáo",
};

export function profileStatusLabel(status: string) {
  return profileStatusLabels[status] ?? "Trạng thái khác";
}

export function commissionStatusLabel(status: string) {
  return commissionStatusLabels[status] ?? "Trạng thái khác";
}

export function ruleStatusLabel(status: string) {
  return ruleStatusLabels[status] ?? "Trạng thái khác";
}

export function affiliateServiceLabel(serviceCode: string) {
  return serviceLabels[serviceCode] ?? "Dịch vụ khác";
}

export function basisPointsAsPercent(basisPoints: number) {
  return new Intl.NumberFormat("vi-VN", {
    style: "percent",
    maximumFractionDigits: 2,
  }).format(basisPoints / 10_000);
}
