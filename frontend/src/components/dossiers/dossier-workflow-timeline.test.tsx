import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DossierWorkflowTimeline } from "@/components/dossiers/dossier-workflow-timeline";

describe("DossierWorkflowTimeline", () => {
  it("shows the active stage and upcoming user-facing stages", () => {
    render(<DossierWorkflowTimeline history={[]} status="PRECHECK" />);

    expect(screen.getByText("Từ chuẩn bị đến nhận chứng thư")).toBeDefined();
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
