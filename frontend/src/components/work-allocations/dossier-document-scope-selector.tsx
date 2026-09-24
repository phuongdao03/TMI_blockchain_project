import { FileText, ShieldCheck, UsersRound } from "lucide-react";

import type { ReviewEvidenceSnapshot, StaffAccount } from "@/lib/api/types";

type ScopeReviewerIds = Record<string, string[]>;

function toggleId(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id];
}

export function DossierDocumentScopeSelector({
  evidences,
  reviewers,
  selectedEvidenceIds,
  scopeReviewerIds,
  dualReviewEvidenceIds,
  onToggleEvidence,
  onToggleReviewer,
  onToggleDualReview,
}: {
  evidences: ReviewEvidenceSnapshot[];
  reviewers: StaffAccount[];
  selectedEvidenceIds: string[];
  scopeReviewerIds: ScopeReviewerIds;
  dualReviewEvidenceIds: string[];
  onToggleEvidence: (evidenceId: string) => void;
  onToggleReviewer: (evidenceId: string, reviewerId: string) => void;
  onToggleDualReview: (evidenceId: string) => void;
}) {
  if (evidences.length === 0) {
    return (
      <p className="mt-3 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
        Version hồ sơ này chưa có tài liệu để phân công.
      </p>
    );
  }

  return (
    <fieldset className="mt-6">
      <legend className="flex items-center gap-2 text-sm font-bold text-neutral-800 dark:text-neutral-100">
        <FileText aria-hidden="true" className="size-4 text-primary-700" />
        Tài liệu và phạm vi thẩm định
      </legend>
      <p className="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
        Chọn từng tài liệu, sau đó gán người chịu trách nhiệm cho đúng phạm vi.
      </p>
      <div className="mt-3 space-y-3">
        {evidences.map((evidence) => {
          const isSelected = selectedEvidenceIds.includes(evidence.id);
          const reviewerIds = scopeReviewerIds[evidence.id] ?? [];
          const isDualReview = dualReviewEvidenceIds.includes(evidence.id);
          return (
            <section
              className="rounded-xl border border-neutral-200 p-4 dark:border-neutral-700"
              key={evidence.id}
            >
              <label className="flex min-h-6 cursor-pointer items-start gap-3 text-sm font-bold text-neutral-900 dark:text-white">
                <input
                  checked={isSelected}
                  className="mt-0.5 size-4 accent-primary-700"
                  onChange={() => onToggleEvidence(evidence.id)}
                  type="checkbox"
                />
                <span>
                  {evidence.title}
                  <span className="mt-1 block text-xs font-normal text-neutral-500 dark:text-neutral-400">
                    {evidence.evidenceType}
                    {evidence.description ? ` · ${evidence.description}` : ""}
                  </span>
                </span>
              </label>
              {isSelected ? (
                <div className="mt-4 border-t border-neutral-200 pt-4 dark:border-neutral-800">
                  <label className="flex min-h-6 items-center gap-2 text-sm font-semibold text-neutral-800 dark:text-neutral-100">
                    <input
                      checked={isDualReview}
                      className="size-4 accent-primary-700"
                      onChange={() => onToggleDualReview(evidence.id)}
                      type="checkbox"
                    />
                    <ShieldCheck
                      aria-hidden="true"
                      className="size-4 text-primary-700"
                    />
                    Yêu cầu thẩm định kép
                  </label>
                  {reviewers.length === 0 ? (
                    <p className="mt-3 text-sm text-amber-800 dark:text-amber-200">
                      Hãy chọn ít nhất một người trong nhóm thẩm định trước.
                    </p>
                  ) : (
                    <fieldset className="mt-3">
                      <legend className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-neutral-600 dark:text-neutral-300">
                        <UsersRound aria-hidden="true" className="size-3.5" />
                        Người chịu trách nhiệm
                      </legend>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        {reviewers.map((reviewer) => (
                          <label
                            className="flex min-h-10 items-center gap-2 rounded-lg border border-neutral-200 px-3 text-sm text-neutral-800 has-[:checked]:border-primary-500 has-[:checked]:bg-primary-50 dark:border-neutral-700 dark:text-neutral-100 dark:has-[:checked]:bg-primary-950"
                            key={reviewer.id}
                          >
                            <input
                              aria-label={`Phân công ${reviewer.email} · ${evidence.title}`}
                              checked={reviewerIds.includes(reviewer.id)}
                              className="size-4 accent-primary-700"
                              onChange={() =>
                                onToggleReviewer(evidence.id, reviewer.id)
                              }
                              type="checkbox"
                            />
                            <span className="truncate">{reviewer.email}</span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  )}
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
    </fieldset>
  );
}

export function toggleScopeReviewer(
  values: ScopeReviewerIds,
  evidenceId: string,
  reviewerId: string,
): ScopeReviewerIds {
  return {
    ...values,
    [evidenceId]: toggleId(values[evidenceId] ?? [], reviewerId),
  };
}
