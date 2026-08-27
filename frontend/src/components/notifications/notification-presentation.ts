import type { NotificationItem } from "@/lib/api/types";

export type NotificationTone = "action" | "success" | "warning" | "info";

export interface NotificationPresentation {
  actionLabel: string;
  actionPath: string | null;
  groupLabel: string;
  tone: NotificationTone;
}

const EVENT_PRESENTATION: Record<
  string,
  Omit<NotificationPresentation, "actionPath">
> = {
  "dossier.submitted": {
    actionLabel: "Xem hồ sơ",
    groupLabel: "Hồ sơ",
    tone: "info",
  },
  "dossier.supplement_requested": {
    actionLabel: "Bổ sung hồ sơ",
    groupLabel: "Cần xử lý",
    tone: "warning",
  },
  "review.assignment_created": {
    actionLabel: "Bắt đầu thẩm định",
    groupLabel: "Công việc mới",
    tone: "action",
  },
  "review.completed": {
    actionLabel: "Xem kết quả",
    groupLabel: "Thẩm định",
    tone: "success",
  },
  "certificate.issued": {
    actionLabel: "Xem chứng thư",
    groupLabel: "Chứng thư",
    tone: "success",
  },
  "certificate.revoked": {
    actionLabel: "Xem chi tiết",
    groupLabel: "Chứng thư",
    tone: "warning",
  },
  "blockchain.anchored": {
    actionLabel: "Xem xác lập",
    groupLabel: "Blockchain",
    tone: "success",
  },
  "content_report.created": {
    actionLabel: "Kiểm tra nội dung",
    groupLabel: "Cần xử lý",
    tone: "warning",
  },
};

function safeInternalPath(value: unknown): string | null {
  if (typeof value !== "string") return null;
  if (!value.startsWith("/") || value.startsWith("//")) return null;
  return value;
}

export function presentNotification(
  item: NotificationItem,
): NotificationPresentation {
  const configured = EVENT_PRESENTATION[item.type] ?? {
    actionLabel: "Xem thông báo",
    groupLabel: "Cập nhật",
    tone: "info" as const,
  };
  return {
    ...configured,
    actionPath: safeInternalPath(item.data.actionPath),
  };
}

export function formatNotificationTime(value: string, now = Date.now()): string {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "";
  const elapsedMinutes = Math.max(0, Math.floor((now - timestamp) / 60_000));
  if (elapsedMinutes < 1) return "Vừa xong";
  if (elapsedMinutes < 60) return `${elapsedMinutes} phút trước`;
  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) return `${elapsedHours} giờ trước`;
  const elapsedDays = Math.floor(elapsedHours / 24);
  if (elapsedDays < 7) return `${elapsedDays} ngày trước`;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(timestamp));
}
