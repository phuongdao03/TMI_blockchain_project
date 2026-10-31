import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { VerdictReviewForm } from "@/components/reviews/verdict-review-form";
import type { ReviewRubric } from "@/lib/api/types";

const rubric: ReviewRubric = {
  version: "2026.3",
  title: "Thẩm định nguồn gốc",
  assessmentMethod: "VERDICT",
  evidencePolicyVersion: "2026.1",
  gates: [],
  criteria: [
    {
      key: "origin",
      label: "Nguồn gốc",
      description: "Đối chiếu thông tin nguồn gốc",
    },
  ],
};

it("focuses one criterion and preserves edits when moving between criteria", async () => {
  const user = userEvent.setup();
  const save = vi.fn().mockResolvedValue(undefined);
  const submit = vi.fn().mockResolvedValue(undefined);
  render(
    <VerdictReviewForm
      rubric={{
        ...rubric,
        criteria: [
          ...rubric.criteria,
          { key: "value", label: "Giá trị", description: "Đối chiếu giá trị" },
        ],
      }}
      evidences={[]}
      initialReview={null}
      isSaving={false}
      isSubmitting={false}
      onSave={save}
      onSubmit={submit}
      readOnly={false}
      requireEvidenceAssessments={false}
    />,
  );
  expect(screen.queryByRole("radio", { name: "Giá trị: Đáp ứng" })).toBeNull();
  await user.type(
    screen.getByLabelText("Nhận định Nguồn gốc"),
    "Nguồn được đối chiếu độc lập.",
  );
  await user.click(
    screen.getByRole("radio", { name: "Nguồn gốc: Chưa đủ căn cứ" }),
  );
  await user.click(screen.getByRole("button", { name: "Tiêu chí tiếp theo" }));
  expect(screen.getByRole("radio", { name: "Giá trị: Đáp ứng" })).toBeDefined();
  expect(
    screen.queryByRole("radio", { name: "Nguồn gốc: Đáp ứng" }),
  ).toBeNull();
  await user.click(screen.getByRole("button", { name: "Tiêu chí trước" }));
  expect(screen.getByLabelText("Nhận định Nguồn gốc")).toHaveProperty(
    "value",
    "Nguồn được đối chiếu độc lập.",
  );
  expect(
    screen.getByRole("radio", { name: "Nguồn gốc: Chưa đủ căn cứ" }),
  ).toHaveProperty("checked", true);
  await user.click(
    screen.getByRole("button", { name: "Gửi kết quả thẩm định" }),
  );
  await waitFor(() =>
    expect(screen.getByRole("radio", { name: "Giá trị: Đáp ứng" })).toBe(
      document.activeElement,
    ),
  );
  expect(submit).not.toHaveBeenCalled();
});

it("can request sources for insufficient basis without manufacturing an evidence link", async () => {
  const user = userEvent.setup();
  const save = vi.fn().mockResolvedValue(undefined);
  render(
    <VerdictReviewForm
      rubric={rubric}
      evidences={[]}
      initialReview={null}
      isSaving={false}
      isSubmitting={false}
      onSave={save}
      onSubmit={vi.fn()}
      readOnly={false}
      requireEvidenceAssessments={false}
    />,
  );
  await user.click(
    screen.getByRole("radio", { name: "Nguồn gốc: Chưa đủ căn cứ" }),
  );
  await user.type(
    screen.getByLabelText("Nhận định Nguồn gốc"),
    "Chưa có nguồn độc lập về niên đại được khai báo.",
  );
  await user.type(
    screen.getByLabelText("Phản hồi gửi người nộp"),
    "Vui lòng bổ sung tư liệu có niên đại hoặc giải trình nguồn thông tin.",
  );
  await user.click(
    screen.getByRole("button", { name: "Gửi kết quả thẩm định" }),
  );
  expect(save).toHaveBeenCalledWith(
    expect.objectContaining({
      recommendation: "SUPPLEMENT",
      criterionVerdicts: {
        origin: expect.objectContaining({
          outcome: "INSUFFICIENT_BASIS",
          evidenceMediaIds: [],
        }),
      },
    }),
  );
  expect(screen.getByRole("button", { name: "Xác nhận gửi" })).toBeDefined();
});

it("shows frozen applicant claims without adopting them as the reviewer's conclusion", () => {
  render(
    <VerdictReviewForm
      rubric={rubric}
      claims={[
        {
          id: "claim-1",
          criterionKey: "origin",
          statement: "Tác phẩm được sáng tác độc lập năm 2024.",
          evidenceMediaIds: [],
        },
      ]}
      evidences={[]}
      initialReview={null}
      isSaving={false}
      isSubmitting={false}
      onSave={vi.fn()}
      onSubmit={vi.fn()}
      readOnly={false}
      requireEvidenceAssessments={false}
    />,
  );
  expect(
    screen.getByText("Tác phẩm được sáng tác độc lập năm 2024."),
  ).toBeDefined();
  expect(
    screen.getByRole("radio", { name: "Nguồn gốc: Đáp ứng" }),
  ).toHaveProperty("checked", false);
  expect(
    screen.getByText(/Nội dung tự khai cần được đối chiếu độc lập/),
  ).toBeDefined();
});
