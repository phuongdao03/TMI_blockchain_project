"use client";

import { ClipboardCheck, FileStack } from "lucide-react";

import { DossierAllocationDetails } from "@/components/work-allocations/dossier-allocation-details";
import { ApiError } from "@/lib/api/client";
import type { StaffAccount } from "@/lib/api/types";

import { useDossierAllocationComposer } from "./use-dossier-allocation-composer";

const fieldClass =
  "mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950 outline-none transition focus:border-primary-600 focus:ring-2 focus:ring-primary-100 dark:border-neutral-700 dark:bg-neutral-950 dark:text-neutral-50 dark:focus:border-primary-400 dark:focus:ring-primary-950";

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Chưa thể hoàn tất phân công. Dữ liệu đã được giữ nguyên để bạn kiểm tra và thử lại.";
}

export function DossierAllocationForm({
  staff,
  onSaved,
}: {
  staff: StaffAccount[];
  onSaved: () => Promise<void>;
}) {
  const composer = useDossierAllocationComposer({ staff, onSaved });

  return (
    <form
      aria-label="Tạo phân công hồ sơ thẩm định"
      className="rounded-2xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900 sm:p-6"
      onSubmit={composer.submit}
    >
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-100 text-primary-800 dark:bg-primary-950 dark:text-primary-200">
          <FileStack aria-hidden="true" className="size-5" />
        </span>
        <div>
          <h2 className="text-xl font-bold text-neutral-950 dark:text-white">
            Phân công hồ sơ thẩm định
          </h2>
          <p className="mt-1 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
            Gắn từng tài liệu của version hiện tại với người chịu trách nhiệm và
            xác nhận phạm vi trước khi kích hoạt.
          </p>
        </div>
      </div>

      <label className="mt-6 block text-sm font-bold text-neutral-800 dark:text-neutral-100">
        Hồ sơ cần thẩm định
        <select
          className={fieldClass}
          disabled={composer.dossiers.isPending || composer.dossiers.isError}
          onChange={(event) => composer.selectDossier(event.target.value)}
          value={composer.selectedDossierId}
        >
          <option value="">
            {composer.dossiers.isPending
              ? "Đang tải hồ sơ..."
              : "Chọn hồ sơ đang thẩm định"}
          </option>
          {(composer.dossiers.data?.data ?? []).map((dossier) => (
            <option key={dossier.dossierId} value={dossier.dossierId}>
              {dossier.dossierCode} · {dossier.dossierTitle} · Version{" "}
              {dossier.versionNo}
            </option>
          ))}
        </select>
      </label>
      {composer.dossiers.isError ? (
        <p className="mt-2 text-sm text-red-700 dark:text-red-300" role="alert">
          Chưa thể tải hồ sơ đang thẩm định.
        </p>
      ) : null}
      {composer.dossierDetail.isPending ? (
        <p
          className="mt-4 text-sm text-neutral-600 dark:text-neutral-300"
          role="status"
        >
          Đang tải version hồ sơ và tài liệu...
        </p>
      ) : null}
      {composer.dossierDetail.data ? (
        <DossierAllocationDetails
          description={composer.description}
          detail={composer.dossierDetail.data}
          dualReviewEvidenceIds={composer.dualReviewEvidenceIds}
          dueAt={composer.dueAt}
          objective={composer.objective}
          onDescriptionChange={composer.setDescription}
          onDualReviewChange={composer.setDualReviewEvidenceIds}
          onDueAtChange={composer.setDueAt}
          onObjectiveChange={composer.setObjective}
          onPriorityChange={composer.setPriority}
          onScopeReviewersChange={composer.setScopeReviewerIds}
          onToggleEvidence={composer.toggleEvidence}
          onToggleReviewer={composer.toggleReviewer}
          priority={composer.priority}
          scopeReviewerIds={composer.scopeReviewerIds}
          selectedEvidenceIds={composer.selectedEvidenceIds}
          selectedReviewerIds={composer.selectedReviewerIds}
          selectedReviewers={composer.selectedReviewers}
          staff={staff}
        />
      ) : null}
      {composer.formError || composer.createAndActivate.error ? (
        <p
          className="mt-5 text-sm font-semibold text-red-700 dark:text-red-300"
          role="alert"
        >
          {composer.formError ?? errorMessage(composer.createAndActivate.error)}
        </p>
      ) : null}
      <button
        className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary-700 px-5 text-sm font-bold text-white transition hover:bg-primary-800 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60 dark:bg-primary-400 dark:text-neutral-950 dark:hover:bg-primary-300"
        disabled={
          composer.createAndActivate.isPending || !composer.dossierDetail.data
        }
        type="submit"
      >
        <ClipboardCheck aria-hidden="true" className="size-4" />
        {composer.createAndActivate.isPending
          ? "Đang ghi nhận..."
          : "Tạo và kích hoạt phân công"}
      </button>
    </form>
  );
}
