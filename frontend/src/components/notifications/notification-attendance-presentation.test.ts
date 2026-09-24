import { describe, expect, it } from "vitest";

import type { NotificationItem } from "@/lib/api/types";

import { presentNotification } from "./notification-presentation";

describe("attendance notification presentation", () => {
  it("routes a pending GPS review to the internal attendance queue", () => {
    const item: NotificationItem = {
      id: "notification-attendance-1",
      type: "HR_ATTENDANCE_LOCATION_REVIEW_REQUIRED",
      title: "Cần xác minh chấm công",
      body: "Có một lượt chấm công cần được xác minh.",
      data: {
        attendanceId: "attendance-1",
        actionPath: "/admin/attendance",
      },
      readAt: null,
      createdAt: "2026-09-22T09:00:00.000Z",
    };

    expect(presentNotification(item)).toMatchObject({
      actionLabel: "Mở hàng chờ xác minh",
      actionPath: "/admin/attendance",
      groupLabel: "Chấm công",
      tone: "warning",
    });
  });
});
