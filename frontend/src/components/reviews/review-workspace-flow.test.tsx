import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { ReviewWorkspace } from "@/components/reviews/review-workspace";

const getMock = vi.hoisted(() => vi.fn());
const submitMock = vi.hoisted(() => vi.fn());
const declareConflictMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  reviewApi: {
    get: getMock,
    saveDraft: vi.fn(),
    submit: submitMock,
    declareConflict: declareConflictMock,
  },
}));
vi.mock("@/components/reviews/evidence-viewer", () => ({
  EvidenceViewer: () => <div>Bằng chứng</div>,
}));
vi.mock("@/components/reviews/review-assistance-panel", () => ({
  ReviewAssistancePanel: () => null,
}));
vi.mock("@/components/reviews/five-t-scorecard", () => ({
  FiveTScorecard: ({ onSubmit }: { onSubmit: () => Promise<void> }) => (
    <button onClick={() => void onSubmit()} type="button">
      Gửi kết quả
    </button>
  ),
}));

const detail = {
  assignment: {
    id: "assignment-1",
    status: "IN_PROGRESS",
    dueAt: null,
  },
  dossierCode: "HS-2026-01",
  dossierTitle: "Hồ sơ văn hóa",
  versionNo: 1,
  canonicalHash: "a".repeat(64),
  snapshotJson: {
    schemaVersion: 1,
    dossier: { summary: "Giới thiệu hồ sơ." },
    evidences: [],
  },
  review: null,
};

beforeEach(() => vi.resetAllMocks());

it("guides the reviewer before and after submitting a report", async () => {
  getMock.mockResolvedValue(detail);
  submitMock.mockResolvedValue({
    id: "review-1",
    submittedAt: "2026-10-07T08:00:00Z",
  });
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ReviewWorkspace assignmentId="assignment-1" />
    </QueryClientProvider>,
  );

  expect(
    await screen.findByText("Việc cần làm · Hoàn tất báo cáo thẩm định"),
  ).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Gửi kết quả" }));

  expect(await screen.findByText("Đã gửi báo cáo cho Admin")).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Về hàng đợi" }).getAttribute("href"),
  ).toBe("/reviews");
});

it("shows the same next step when a submitted report is reopened", async () => {
  getMock.mockResolvedValue({
    ...detail,
    assignment: { ...detail.assignment, status: "SUBMITTED" },
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ReviewWorkspace assignmentId="assignment-1" />
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Đã gửi báo cáo cho Admin")).toBeTruthy();
});

it("lets an assigned reviewer confirm no conflict and continue to the report", async () => {
  const assigned = {
    ...detail,
    assignment: { ...detail.assignment, status: "ASSIGNED" },
  };
  getMock.mockResolvedValueOnce(assigned).mockResolvedValue({
    ...detail,
    assignment: { ...detail.assignment, status: "IN_PROGRESS" },
  });
  declareConflictMock.mockResolvedValue({
    ...detail.assignment,
    status: "IN_PROGRESS",
  });
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ReviewWorkspace assignmentId="assignment-1" />
    </QueryClientProvider>,
  );

  await user.click(
    await screen.findByRole("button", { name: "Không có xung đột lợi ích" }),
  );

  expect(declareConflictMock).toHaveBeenCalledWith("assignment-1", {
    hasConflict: false,
  });
  expect(
    await screen.findByText("Việc cần làm · Hoàn tất báo cáo thẩm định"),
  ).toBeTruthy();
});

it("requires a reason before declaring a conflict", async () => {
  const assigned = {
    ...detail,
    assignment: { ...detail.assignment, status: "ASSIGNED" },
  };
  getMock.mockResolvedValueOnce(assigned).mockResolvedValue({
    ...detail,
    assignment: { ...detail.assignment, status: "CONFLICTED" },
  });
  declareConflictMock.mockResolvedValue({
    ...detail.assignment,
    status: "CONFLICTED",
  });
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ReviewWorkspace assignmentId="assignment-1" />
    </QueryClientProvider>,
  );

  await user.click(
    await screen.findByRole("button", { name: "Có xung đột lợi ích" }),
  );
  expect(declareConflictMock).not.toHaveBeenCalled();
  await user.type(
    screen.getByRole("textbox", { name: "Lý do xung đột" }),
    "Có quan hệ với người nộp hồ sơ",
  );
  await user.click(screen.getByRole("button", { name: "Xác nhận xung đột" }));

  expect(declareConflictMock).toHaveBeenCalledWith("assignment-1", {
    hasConflict: true,
    reason: "Có quan hệ với người nộp hồ sơ",
  });
  expect(await screen.findByText("Phân công đã kết thúc")).toBeTruthy();
});
