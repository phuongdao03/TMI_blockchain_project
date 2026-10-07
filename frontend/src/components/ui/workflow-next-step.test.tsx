import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { WorkflowNextStep } from "@/components/ui/workflow-next-step";

it("announces completed work and provides a real next destination", () => {
  render(
    <WorkflowNextStep
      action={{ href: "/reviews", label: "Xem hàng đợi" }}
      description="Admin sẽ xem báo cáo trước khi ra quyết định."
      title="Đã gửi báo cáo"
      tone="success"
    />,
  );

  expect(screen.getByRole("status").textContent).toContain("Đã gửi báo cáo");
  expect(screen.getByRole("status").textContent).toContain(
    "Admin sẽ xem báo cáo",
  );
  expect(
    screen.getByRole("link", { name: "Xem hàng đợi" }).getAttribute("href"),
  ).toBe("/reviews");
});

it("keeps standing guidance out of the live region", () => {
  render(
    <WorkflowNextStep
      description="Chọn người kiểm duyệt để bắt đầu."
      title="Bước 1 · Phân công"
    />,
  );

  expect(screen.getByText("Bước 1 · Phân công")).toBeTruthy();
  expect(screen.queryByRole("status")).toBeNull();
});
