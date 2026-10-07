import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/auth/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/components/admin/operations-dashboard", () => ({
  OperationsDashboard: () => <div>Chỉ số vận hành</div>,
}));

import AdminPortalPage from "@/app/(dashboard)/admin/page";

describe("AdminPortalPage", () => {
  it("puts the dossier workflow before operational metrics", () => {
    const { container } = render(<AdminPortalPage />);

    expect(
      screen.getByRole("heading", { name: "Bắt đầu xử lý hồ sơ" }),
    ).toBeDefined();
    expect(
      screen.getByRole("link", { name: /Quyết định phí/ }).getAttribute("href"),
    ).toBe("/admin/payments");
    expect(
      screen
        .getByRole("link", { name: /Tiếp nhận và phân công/ })
        .getAttribute("href"),
    ).toBe("/admin/reviews");
    expect(
      screen
        .getByRole("link", { name: /Theo dõi thẩm định/ })
        .getAttribute("href"),
    ).toBe("/admin/dashboard");
    expect(
      screen
        .getByRole("link", { name: /Hoàn tất phát hành/ })
        .getAttribute("href"),
    ).toBe("/admin/certificates");
    const workflow = container.querySelector('[aria-label="Quy trình hồ sơ"]');
    const metrics = screen.getByText("Chỉ số vận hành");
    expect(
      (workflow?.compareDocumentPosition(metrics) ?? 0) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
