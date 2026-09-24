import { UsersRound } from "lucide-react";

import {
  DossierDocumentScopeSelector,
  toggleScopeReviewer,
} from "@/components/work-allocations/dossier-document-scope-selector";
import type {
  AdminReviewDossierDetail,
  StaffAccount,
  WorkAllocationPriority,
} from "@/lib/api/types";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100 dark:border-neutral-700 dark:bg-neutral-950 dark:text-neutral-50 dark:focus:border-primary-400 dark:focus:ring-primary-950";

const priorityLabels: Record<WorkAllocationPriority, string> = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
  CRITICAL: "Khẩn cấp",
};

export function DossierAllocationDetails({
  detail,
  staff,
  selectedReviewerIds,
  selectedReviewers,
  selectedEvidenceIds,
  scopeReviewerIds,
  dualReviewEvidenceIds,
  objective,
  description,
  dueAt,
  priority,
  onObjectiveChange,
  onDescriptionChange,
  onDueAtChange,
  onPriorityChange,
  onToggleReviewer,
  onToggleEvidence,
  onScopeReviewersChange,
  onDualReviewChange,
}: {
  detail: AdminReviewDossierDetail;
  staff: StaffAccount[];
  selectedReviewerIds: string[];
  selectedReviewers: StaffAccount[];
  selectedEvidenceIds: string[];
  scopeReviewerIds: Record<string, string[]>;
  dualReviewEvidenceIds: string[];
  objective: string;
  description: string;
  dueAt: string;
  priority: WorkAllocationPriority;
  onObjectiveChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onDueAtChange: (value: string) => void;
  onPriorityChange: (value: WorkAllocationPriority) => void;
  onToggleReviewer: (reviewerId: string) => void;
  onToggleEvidence: (evidenceId: string) => void;
  onScopeReviewersChange: (value: Record<string, string[]>) => void;
  onDualReviewChange: (value: string[]) => void;
}) {
  return (
    <>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-bold text-neutral-800 dark:text-neutral-100">
          Mục tiêu phân công
          <input
            className={fieldClass}
            maxLength={240}
            onChange={(event) => onObjectiveChange(event.target.value)}
            value={objective}
          />
        </label>
        <label className="text-sm font-bold text-neutral-800 dark:text-neutral-100">
          Mức độ ưu tiên
          <select
            className={fieldClass}
            onChange={(event) =>
              onPriorityChange(event.target.value as WorkAllocationPriority)
            }
            value={priority}
          >
            {Object.entries(priorityLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-bold text-neutral-800 dark:text-neutral-100">
          Hạn hoàn thành
          <input
            className={fieldClass}
            onChange={(event) => onDueAtChange(event.target.value)}
            type="datetime-local"
            value={dueAt}
          />
        </label>
        <label className="text-sm font-bold text-neutral-800 dark:text-neutral-100">
          Ghi chú{" "}
          <span className="font-normal text-neutral-500">(không bắt buộc)</span>
          <textarea
            className={`${fieldClass} min-h-24 py-3`}
            maxLength={10000}
            onChange={(event) => onDescriptionChange(event.target.value)}
            value={description}
          />
        </label>
      </div>
      <fieldset className="mt-6">
        <legend className="flex items-center gap-2 text-sm font-bold text-neutral-800 dark:text-neutral-100">
          <UsersRound aria-hidden="true" className="size-4 text-primary-700" />{" "}
          Nhóm thẩm định
        </legend>
        <p className="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
          Chỉ người trong nhóm này mới có thể được gán cho tài liệu bên dưới.
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {staff.map((person) => (
            <label
              className="flex min-h-11 items-center gap-3 rounded-xl border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-800 has-[:checked]:border-primary-500 has-[:checked]:bg-primary-50 dark:border-neutral-700 dark:text-neutral-100 dark:has-[:checked]:bg-primary-950"
              key={person.id}
            >
              <input
                aria-label={person.email}
                checked={selectedReviewerIds.includes(person.id)}
                className="size-4 accent-primary-700"
                onChange={() => onToggleReviewer(person.id)}
                type="checkbox"
              />
              <span className="min-w-0 truncate">{person.email}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <DossierDocumentScopeSelector
        dualReviewEvidenceIds={dualReviewEvidenceIds}
        evidences={detail.snapshotJson.evidences}
        onToggleDualReview={(evidenceId) =>
          onDualReviewChange(
            dualReviewEvidenceIds.includes(evidenceId)
              ? dualReviewEvidenceIds.filter((id) => id !== evidenceId)
              : [...dualReviewEvidenceIds, evidenceId],
          )
        }
        onToggleEvidence={onToggleEvidence}
        onToggleReviewer={(evidenceId, reviewerId) =>
          onScopeReviewersChange(
            toggleScopeReviewer(scopeReviewerIds, evidenceId, reviewerId),
          )
        }
        reviewers={selectedReviewers}
        scopeReviewerIds={scopeReviewerIds}
        selectedEvidenceIds={selectedEvidenceIds}
      />
    </>
  );
}
