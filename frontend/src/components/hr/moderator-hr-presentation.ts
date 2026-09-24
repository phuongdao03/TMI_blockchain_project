import type { ModeratorHrDashboardSummary } from "@/lib/api/types";

export function attendancePresentation(summary: ModeratorHrDashboardSummary) {
  const actionLabel = "Xem chấm công";
  if (!summary.workDate || !summary.timezone) {
    return {
      actionLabel,
      title: "Chưa có lịch làm việc",
      description:
        "Cần được phân công địa điểm và lịch làm việc trước khi có thể chấm công.",
    };
  }
  const status = summary.attendanceStatus;
  if (status === null) {
    return {
      actionLabel: "Mở chấm công",
      title: "Chưa chấm công",
      description: "Bạn có thể ghi nhận giờ vào cho ngày làm việc hiện tại.",
    };
  }
  const recordedStates = {
    PENDING: [
      "Chấm công đang chờ xác minh",
      "Lượt chấm công sẽ được cập nhật sau khi được xem xét.",
    ],
    REJECTED: [
      "Chấm công cần trao đổi",
      "Lượt chấm công chưa được chấp nhận. Hãy xem chi tiết để xử lý.",
    ],
    LEAVE: [
      "Đã ghi nhận nghỉ phép",
      "Ngày làm việc này được ghi nhận là nghỉ phép.",
    ],
    ABSENT: [
      "Đã ghi nhận vắng mặt",
      "Hãy kiểm tra chi tiết và liên hệ quản trị viên nếu cần điều chỉnh.",
    ],
    HALF_DAY: [
      "Đã ghi nhận nửa ngày công",
      "Xem chi tiết để kiểm tra thời gian đã được ghi nhận.",
    ],
  } as const;
  if (status in recordedStates) {
    const [title, description] =
      recordedStates[status as keyof typeof recordedStates];
    return { actionLabel, title, description };
  }
  if (summary.checkInAt && summary.checkOutAt) {
    return {
      actionLabel,
      title: "Đã ghi nhận giờ vào và giờ ra",
      description: "Thời gian chấm công đã được lưu cho ngày làm việc này.",
    };
  }
  if (summary.checkInAt) {
    return {
      actionLabel: "Mở chấm công",
      title: "Đã ghi nhận giờ vào",
      description: "Bạn có thể mở chấm công khi cần ghi nhận giờ ra.",
    };
  }
  return {
    actionLabel,
    title: "Đã có bản ghi chấm công",
    description:
      "Chưa có giờ vào được ghi nhận. Hãy kiểm tra chi tiết chấm công.",
  };
}

export function formatWorksiteTime(value: string | null, timezone: string) {
  if (!value) return "Chưa ghi nhận";
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.valueOf())) return "Không xác định";
  return timestamp.toLocaleTimeString("vi-VN", {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
}

export function formatUpdatedAt(value: string, timezone: string | null) {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.valueOf())) return null;
  return timestamp.toLocaleString("vi-VN", {
    timeZone: timezone ?? "UTC",
    dateStyle: "short",
    timeStyle: "short",
  });
}
