import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useReviewAutosave } from "@/components/reviews/use-review-autosave";
import type { ReviewDraft } from "@/lib/api/types";

const initialDraft: ReviewDraft = {
  truthScore: null,
  transparencyScore: null,
  ownershipScore: null,
  professionalismScore: null,
  respectScore: null,
  criterionComments: {},
  criterionEvidence: {},
  findings: [],
  checklistAnswers: {},
  applicantFeedback: null,
  recommendation: null,
  privateNote: null,
  gateAnswers: {},
  specialistAnswers: {},
  criterionVerdicts: {},
  evidenceAssessments: {},
};

describe("useReviewAutosave", () => {
  it("does not save the same draft again when the parent callback changes", async () => {
    let finishSave: (() => void) | undefined;
    const save = vi.fn(
      (draft: ReviewDraft) =>
        new Promise<void>((resolve) => {
          void draft;
          finishSave = resolve;
        }),
    );
    const initialOnSave: (draft: ReviewDraft) => Promise<void> = save;
    const changedDraft = { ...initialDraft, privateNote: "Đã kiểm tra video." };
    const { rerender } = renderHook(
      ({
        draft,
        onSave,
      }: {
        draft: ReviewDraft;
        onSave: (draft: ReviewDraft) => Promise<void>;
      }) => useReviewAutosave({ draft, onSave, readOnly: false, delay: 10 }),
      { initialProps: { draft: initialDraft, onSave: initialOnSave } },
    );

    rerender({ draft: changedDraft, onSave: save });
    await vi.waitFor(() => expect(save).toHaveBeenCalledTimes(1));
    rerender({
      draft: changedDraft,
      onSave: (draft) => save(draft),
    });

    await new Promise((resolve) => window.setTimeout(resolve, 30));
    expect(save).toHaveBeenCalledTimes(1);
    finishSave?.();
    await vi.waitFor(() => expect(save).toHaveBeenCalledTimes(1));
  });
});

it("serializes manual save with autosave and only reports saved after acknowledgement", async () => {
  let finish: (() => void) | undefined;
  const save = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  const { result, rerender } = renderHook(
    ({ draft }) =>
      useReviewAutosave({ draft, onSave: save, readOnly: false, delay: 10 }),
    { initialProps: { draft: initialDraft } },
  );
  const changed = { ...initialDraft, privateNote: "Changed" };
  rerender({ draft: changed });
  expect(result.current.status).toBe("pending");
  await vi.waitFor(() => expect(save).toHaveBeenCalledTimes(1));
  let manual: Promise<void>;
  act(() => {
    manual = result.current.save(changed);
  });
  expect(save).toHaveBeenCalledTimes(1);
  await act(async () => {
    finish?.();
    await manual;
  });
  expect(result.current.status).toBe("saved");
  expect(save).toHaveBeenCalledTimes(1);
});
