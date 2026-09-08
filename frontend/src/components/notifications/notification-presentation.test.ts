import { describe, expect, it } from "vitest";

import type { NotificationItem } from "@/lib/api/types";

import {
  formatNotificationTime,
  presentNotification,
} from "./notification-presentation";

const base: NotificationItem = {
  id: "notification-1",
  type: "review.assignment_created",
  title: "Phân công thẩm định",
  body: "Bạn có một hồ sơ mới.",
  data: { actionPath: "/reviews/assignment-1" },
  readAt: null,
  createdAt: "2026-08-27T10:00:00.000Z",
};

describe("notification presentation", () => {
  it("routes existing submitted-dossier notifications to the admin queue", () => {
    expect(
      presentNotification(
        {
          ...base,
          type: "dossier.submitted",
          data: { dossier_id: "dossier-1", actionPath: "/dossiers/dossier-1" },
        },
        { adminDossierLinks: true },
      ).actionPath,
    ).toBe("/admin/reviews/dossier-1");
  });

  it("routes existing completed-review notifications to the admin report", () => {
    expect(
      presentNotification(
        {
          ...base,
          type: "review.completed",
          data: { dossier_id: "dossier-1", actionPath: "/dossiers/dossier-1" },
        },
        { adminDossierLinks: true },
      ).actionPath,
    ).toBe("/admin/reviews/dossier-1");
  });

  it("maps a reviewer job to a safe internal action", () => {
    expect(presentNotification(base)).toMatchObject({
      actionLabel: "Bắt đầu thẩm định",
      actionPath: "/reviews/assignment-1",
      groupLabel: "Công việc mới",
    });
  });

  it("rejects external and protocol-relative action paths", () => {
    expect(
      presentNotification({
        ...base,
        data: { actionPath: "https://evil.test" },
      }).actionPath,
    ).toBeNull();
    expect(
      presentNotification({ ...base, data: { actionPath: "//evil.test" } })
        .actionPath,
    ).toBeNull();
  });

  it("presents the payment-to-signing lifecycle with direct actions", () => {
    expect(
      presentNotification({
        ...base,
        type: "PAYMENT_REQUEST_ISSUED",
        data: { actionPath: "/payments/order-1" },
      }),
    ).toMatchObject({
      actionLabel: "Thanh toán ngay",
      actionPath: "/payments/order-1",
      groupLabel: "Thanh toán",
      tone: "action",
    });

    expect(
      presentNotification({
        ...base,
        type: "DOSSIER_READY_FOR_BLOCKCHAIN",
        data: { actionPath: "/blockchain" },
      }),
    ).toMatchObject({
      actionLabel: "Mở hàng đợi ký",
      actionPath: "/blockchain",
      groupLabel: "Blockchain",
      tone: "action",
    });
  });

  it("formats recent times for quick scanning", () => {
    expect(
      formatNotificationTime(
        "2026-08-27T09:58:00.000Z",
        Date.parse("2026-08-27T10:00:00.000Z"),
      ),
    ).toBe("2 phút trước");
  });
});
