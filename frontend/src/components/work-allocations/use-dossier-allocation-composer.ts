import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, useMemo, useState } from "react";

import { adminReviewApi, workAllocationAdminApi } from "@/lib/api/client";
import type {
  ReviewAssignment,
  StaffAccount,
  WorkAllocationPriority,
} from "@/lib/api/types";

const coverableAssignmentStatuses = new Set([
  "ASSIGNED",
  "IN_PROGRESS",
  "SUBMITTED",
]);
const routingReason =
  "Quản trị viên chuyển hồ sơ sang thẩm định khi giao việc.";

export function useDossierAllocationComposer({
  staff,
  onSaved,
  initialDossier,
}: {
  staff: StaffAccount[];
  onSaved: () => Promise<void>;
  initialDossier?: { dossierId: string; dossierTitle: string };
}) {
  const [selectedDossierId, setSelectedDossierId] = useState(
    initialDossier?.dossierId ?? "",
  );
  const [objective, setObjective] = useState(
    initialDossier ? `Thẩm định: ${initialDossier.dossierTitle}` : "",
  );
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [priority, setPriority] = useState<WorkAllocationPriority>("MEDIUM");
  const [selectedReviewerIds, setSelectedReviewerIds] = useState<string[]>([]);
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<
    string[] | null
  >(null);
  const [scopeReviewerIds, setScopeReviewerIds] = useState<
    Record<string, string[]>
  >({});
  const [dualReviewEvidenceIds, setDualReviewEvidenceIds] = useState<string[]>(
    [],
  );
  const [formError, setFormError] = useState<string | null>(null);
  const dossiers = useQuery({
    queryKey: ["review-dossiers", "allocation-composer"],
    queryFn: () => adminReviewApi.list({ pageSize: 100 }),
  });
  const dossierDetail = useQuery({
    queryKey: ["review-dossier", selectedDossierId, "allocation-composer"],
    queryFn: () => adminReviewApi.get(selectedDossierId),
    enabled: Boolean(selectedDossierId),
  });
  const selectedReviewers = useMemo(
    () => staff.filter((person) => selectedReviewerIds.includes(person.id)),
    [selectedReviewerIds, staff],
  );
  const effectiveSelectedEvidenceIds =
    selectedEvidenceIds ??
    (dossierDetail.data?.snapshotJson.evidences ?? []).map(
      (evidence) => evidence.id,
    );
  const effectiveScopeReviewerIds = Object.fromEntries(
    effectiveSelectedEvidenceIds.map((evidenceId) => [
      evidenceId,
      scopeReviewerIds[evidenceId] ?? selectedReviewerIds,
    ]),
  );
  const selectedEvidences = useMemo(
    () =>
      (dossierDetail.data?.snapshotJson.evidences ?? []).filter((evidence) =>
        effectiveSelectedEvidenceIds.includes(evidence.id),
      ),
    [dossierDetail.data?.snapshotJson.evidences, effectiveSelectedEvidenceIds],
  );

  const createAndActivate = useMutation({
    mutationFn: async () => {
      if (!dossierDetail.data)
        throw new Error("Hồ sơ chưa sẵn sàng để phân công.");
      const detail = await adminReviewApi.get(selectedDossierId);
      if (detail.status === "SUBMITTED") {
        await adminReviewApi.startPrecheck(detail.dossierId, routingReason);
      }
      if (detail.status === "SUBMITTED" || detail.status === "PRECHECK") {
        await adminReviewApi.passPrecheck(detail.dossierId, routingReason);
      }
      const assignmentsByReviewer = new Map<string, ReviewAssignment>();
      detail.assignments.forEach(({ assignment }) => {
        if (coverableAssignmentStatuses.has(assignment.status)) {
          assignmentsByReviewer.set(assignment.reviewerUserId, assignment);
        }
      });
      const reviewerIdsToAssign = selectedReviewerIds.filter(
        (reviewerId) => !assignmentsByReviewer.has(reviewerId),
      );
      const newAssignments = reviewerIdsToAssign.length
        ? await adminReviewApi.assign(
            detail.dossierId,
            reviewerIdsToAssign,
            dueAt ? new Date(dueAt).toISOString() : undefined,
          )
        : [];
      newAssignments.forEach((assignment) => {
        assignmentsByReviewer.set(assignment.reviewerUserId, assignment);
      });
      const dossierVersionId = [...assignmentsByReviewer.values()][0]
        ?.dossierVersionId;
      if (!dossierVersionId) {
        throw new Error("Không xác định được version hồ sơ để tạo phân công.");
      }
      const created = await workAllocationAdminApi.create({
        kind: "DOSSIER_REVIEW",
        objective: objective.trim(),
        description: description.trim() || null,
        dossierId: detail.dossierId,
        dossierVersionId,
        dueAt: dueAt ? new Date(dueAt).toISOString() : null,
        priority,
        scopes: selectedEvidences.map((evidence) => ({
          scopeType: "EVIDENCE",
          dossierEvidenceId: evidence.id,
          requiresDualReview: dualReviewEvidenceIds.includes(evidence.id),
        })),
        members: selectedReviewerIds.map((userId) => ({
          userId,
          responsibility: "REVIEWER",
        })),
      });
      const createdDetail = await workAllocationAdminApi.get(created.id);
      const scopeIdByEvidence = new Map(
        createdDetail.scopes.map((scope) => [
          scope.dossierEvidenceId,
          scope.id,
        ]),
      );
      const scopeCoverage = selectedEvidences.map((evidence) => {
        const scopeId = scopeIdByEvidence.get(evidence.id);
        const reviewAssignmentIds = (
          effectiveScopeReviewerIds[evidence.id] ?? []
        ).map((reviewerId) => assignmentsByReviewer.get(reviewerId)?.id);
        if (
          !scopeId ||
          reviewAssignmentIds.some((assignmentId) => !assignmentId)
        ) {
          throw new Error(
            "Không thể đối chiếu đầy đủ phạm vi tài liệu với phân công thẩm định.",
          );
        }
        return {
          scopeId,
          reviewAssignmentIds: reviewAssignmentIds as string[],
        };
      });
      await workAllocationAdminApi.activate(created.id, scopeCoverage);
    },
    onSuccess: async () => {
      setFormError(null);
      await onSaved();
    },
  });

  function selectDossier(dossierId: string) {
    const dossier = dossiers.data?.data.find(
      (item) => item.dossierId === dossierId,
    );
    setSelectedDossierId(dossierId);
    setObjective(dossier ? `Thẩm định: ${dossier.dossierTitle}` : "");
    setSelectedEvidenceIds(null);
    setScopeReviewerIds({});
    setDualReviewEvidenceIds([]);
    setFormError(null);
  }

  function toggleReviewer(reviewerId: string) {
    setSelectedReviewerIds((selected) =>
      selected.includes(reviewerId)
        ? selected.filter((id) => id !== reviewerId)
        : [...selected, reviewerId],
    );
    setScopeReviewerIds((current) =>
      Object.fromEntries(
        Object.entries(current).map(([evidenceId, reviewerIds]) => [
          evidenceId,
          reviewerIds.filter((id) => id !== reviewerId),
        ]),
      ),
    );
  }

  function toggleEvidence(evidenceId: string) {
    setSelectedEvidenceIds((selected) => {
      const current =
        selected ??
        (dossierDetail.data?.snapshotJson.evidences ?? []).map(
          (evidence) => evidence.id,
        );
      return current.includes(evidenceId)
        ? current.filter((id) => id !== evidenceId)
        : [...current, evidenceId];
    });
    setScopeReviewerIds((current) => {
      const next = { ...current };
      delete next[evidenceId];
      return next;
    });
    setDualReviewEvidenceIds((selected) =>
      selected.filter((id) => id !== evidenceId),
    );
  }

  function toggleScopeReviewer(evidenceId: string, reviewerId: string) {
    const current = effectiveScopeReviewerIds[evidenceId] ?? [];
    setScopeReviewerIds((values) => ({
      ...values,
      [evidenceId]: current.includes(reviewerId)
        ? current.filter((id) => id !== reviewerId)
        : [...current, reviewerId],
    }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!objective.trim() || !dossierDetail.data) {
      setFormError("Chọn hồ sơ và nhập mục tiêu phân công trước khi tiếp tục.");
      return;
    }
    if (selectedReviewerIds.length === 0 || selectedEvidences.length === 0) {
      setFormError("Chọn ít nhất một người thẩm định và một tài liệu.");
      return;
    }
    const invalidScope = selectedEvidences.find((evidence) => {
      const reviewerIds = effectiveScopeReviewerIds[evidence.id] ?? [];
      return (
        reviewerIds.length <
        (dualReviewEvidenceIds.includes(evidence.id) ? 2 : 1)
      );
    });
    if (invalidScope) {
      setFormError(
        `Tài liệu “${invalidScope.title}” chưa có đủ người chịu trách nhiệm.`,
      );
      return;
    }
    setFormError(null);
    createAndActivate.mutate();
  }

  return {
    createAndActivate,
    description,
    dossierDetail,
    dossiers,
    dueAt,
    dualReviewEvidenceIds,
    formError,
    objective,
    priority,
    scopeReviewerIds: effectiveScopeReviewerIds,
    selectedDossierId,
    selectedEvidenceIds: effectiveSelectedEvidenceIds,
    selectedReviewerIds,
    selectedReviewers,
    selectDossier,
    setDescription,
    setDueAt,
    setDualReviewEvidenceIds,
    setObjective,
    setPriority,
    submit,
    toggleEvidence,
    toggleReviewer,
    toggleScopeReviewer,
  };
}
