import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DossierWorkflowTimeline } from "@/components/dossiers/dossier-workflow-timeline";

describe("DossierWorkflowTimeline", () => {
  it("shows publication as complete instead of still receiving a certificate", () => {
    render(
      <DossierWorkflowTimeline
        history={[]}
        status="PUBLISHED"
        submissionFeeRequired
      />,
    );
    expect(screen.getByText("Công bố").closest("li")?.textContent).toContain(
      "Đã hoàn tất",
    );
    expect(screen.queryByText("Đang thực hiện")).toBeNull();
    expect(screen.queryByText("Sắp tới")).toBeNull();
  });
  it("distinguishes an issued certificate from a future publication", () => {
    render(
      <DossierWorkflowTimeline history={[]} status="CERTIFICATE_ISSUED" />,
    );
    expect(screen.getByText("Công bố").closest("li")?.textContent).toContain(
      "Sắp tới",
    );
  });
  it("places unpaid submission before intake without completing future stages", () => {
    render(
      <DossierWorkflowTimeline
        history={[]}
        status="PAYMENT_PENDING"
        submissionFeeRequired
      />,
    );
    const current = screen.getByText("Đang thực hiện").closest("li");
    expect(current?.textContent).toContain("Thanh toán phí nộp");
    expect(
      screen.getByText("Kiểm tra ban đầu").closest("li")?.textContent,
    ).toContain("Sắp tới");
  });
  it("shows the active stage and upcoming user-facing stages", () => {
    render(<DossierWorkflowTimeline history={[]} status="PRECHECK" />);

    expect(screen.getByText("Từ chuẩn bị đến công bố")).toBeDefined();
    expect(screen.getByText("Đang thực hiện")).toBeDefined();
    expect(screen.getAllByText("Sắp tới").length).toBeGreaterThan(0);
  });

  it("surfaces supplement and rejection as exception states", () => {
    const { rerender } = render(
      <DossierWorkflowTimeline history={[]} status="NEEDS_SUPPLEMENT" />,
    );
    expect(screen.getByText("Cần bạn bổ sung")).toBeDefined();

    rerender(<DossierWorkflowTimeline history={[]} status="REJECTED" />);
    expect(screen.getByText("Chưa đủ điều kiện")).toBeDefined();
  });
});
