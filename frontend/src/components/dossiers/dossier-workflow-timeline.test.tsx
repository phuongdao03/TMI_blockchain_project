import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { dossierProgress } from "@/components/dossiers/dossier-progress";

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
    expect(
      screen
        .getAllByText("Công bố")
        .find((el) => el.closest("li"))
        ?.closest("li")?.textContent,
    ).toContain("Đã hoàn tất");
    expect(screen.queryByText("Đang thực hiện")).toBeNull();
    expect(screen.getAllByText("Chưa bắt đầu").length).toBeGreaterThan(0);
  });
  it("distinguishes an issued certificate from a future publication", () => {
    render(
      <DossierWorkflowTimeline history={[]} status="CERTIFICATE_ISSUED" />,
    );
    expect(
      screen
        .getAllByText("Công bố")
        .find((el) => el.closest("li"))
        ?.closest("li")?.textContent,
    ).toContain("Chưa bắt đầu");
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
    ).toContain("Chưa bắt đầu");
  });
  it("shows the active stage and upcoming user-facing stages", () => {
    render(<DossierWorkflowTimeline history={[]} status="PRECHECK" />);

    expect(screen.getByText("Từ chuẩn bị đến công bố")).toBeDefined();
    expect(screen.getByText("Đang thực hiện")).toBeDefined();
    expect(screen.getAllByText("Chưa bắt đầu").length).toBeGreaterThan(0);
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

describe("evidence-based dossier progress", () => {
  it("does not invent completed steps when history is absent", () => {
    const result = dossierProgress({
      status: "UNDER_REVIEW",
      history: [],
      submissionFeeRequired: true,
    });
    expect(result.stages.find((s) => s.key === "intake")?.state).toBe(
      "pending",
    );
    expect(result.stages.find((s) => s.key === "fee")?.state).toBe("pending");
  });
  it("records waiver separately and puts it before review", () => {
    const result = dossierProgress({
      status: "UNDER_REVIEW",
      history: [],
      submissionFeeWaivedAt: "2026-11-01T00:00:00Z",
    });
    expect(result.stages[1]?.key).toBe("fee");
    expect(result.stages[1]?.detail).toBe("Được miễn phí");
    expect(result.stages[1]?.completedAt).toBe("2026-11-01T00:00:00Z");
  });
  it("stops rejected dossiers without completing publication", () => {
    const result = dossierProgress({
      status: "REJECTED",
      history: [],
      submissionFeeRequired: true,
    });
    expect(result.next).toBeNull();
    expect(result.stages.find((s) => s.key === "publication")?.state).toBe(
      "stopped",
    );
  });
  it("keeps legacy payment after decision", () => {
    const result = dossierProgress({ status: "APPROVED", history: [] });
    expect(result.stages.findIndex((s) => s.key === "fee")).toBeGreaterThan(
      result.stages.findIndex((s) => s.key === "decision"),
    );
  });
});

it("uses the stored workflow mode even when no money is due", () => {
  const progress = dossierProgress({
    status: "SUBMITTED",
    history: [],
    submissionFeePolicyMode: "DYNAMIC",
    submissionFeeRequired: false,
  });
  expect(progress.stages[1]?.key).toBe("fee");
});
it("pauses at the real review stage across repeated supplements", () => {
  const history = [
    {
      fromStatus: "UNDER_REVIEW",
      toStatus: "NEEDS_SUPPLEMENT",
      createdAt: "2026-11-01T00:00:00Z",
      note: "First request",
    },
    {
      fromStatus: "NEEDS_SUPPLEMENT",
      toStatus: "UNDER_REVIEW",
      createdAt: "2026-11-02T00:00:00Z",
      note: null,
    },
    {
      fromStatus: "UNDER_REVIEW",
      toStatus: "NEEDS_SUPPLEMENT",
      createdAt: "2026-11-03T00:00:00Z",
      note: "Second request",
    },
  ] as const;
  const progress = dossierProgress({
    status: "NEEDS_SUPPLEMENT",
    history,
    submissionFeePolicyMode: "DYNAMIC",
    submissionFeePaidAt: "2026-10-30T00:00:00Z",
  });
  expect(progress.stages.find((stage) => stage.key === "review")?.state).toBe(
    "supplement",
  );
  expect(progress.stages.find((stage) => stage.key === "review")?.detail).toBe(
    "Second request",
  );
  expect(progress.stages.find((stage) => stage.key === "fee")?.state).toBe(
    "complete",
  );
  expect(progress.next).toBe("Quyết định hồ sơ");
});

it("does not reorder a historical payment made after review", () => {
  const progress = dossierProgress({
    status: "PAID",
    submissionFeeRequired: true,
    submissionFeePaidAt: "2026-10-03T00:00:00Z",
    history: [
      {
        fromStatus: "PRECHECK",
        toStatus: "UNDER_REVIEW",
        createdAt: "2026-10-01T00:00:00Z",
        note: null,
      },
      {
        fromStatus: "APPROVED",
        toStatus: "PAYMENT_PENDING",
        createdAt: "2026-10-02T00:00:00Z",
        note: null,
      },
    ],
  });
  expect(progress.modern).toBe(false);
  expect(
    progress.stages.findIndex((stage) => stage.key === "fee"),
  ).toBeGreaterThan(
    progress.stages.findIndex((stage) => stage.key === "review"),
  );
  expect(
    progress.stages.find((stage) => stage.key === "fee")?.completedAt,
  ).toBe("2026-10-03T00:00:00Z");
});
