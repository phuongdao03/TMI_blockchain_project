"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, Plus } from "lucide-react";
import { useState } from "react";

import { DossierAllocationForm } from "@/components/work-allocations/dossier-allocation-form";
import { GenericAllocationForm } from "@/components/work-allocations/generic-allocation-form";
import { WorkAllocationList } from "@/components/work-allocations/work-allocation-list";
import { WorkflowNextStep } from "@/components/ui/workflow-next-step";
import {
  adminReviewApi,
  staffAccountsApi,
  workAllocationAdminApi,
} from "@/lib/api/client";
import type { AdminReviewDossierSummary } from "@/lib/api/types";

export function WorkAllocationWorkspace() {
  const [isCreating, setIsCreating] = useState(false);
  const [creationKind, setCreationKind] = useState<
    "GENERIC" | "DOSSIER_REVIEW"
  >("DOSSIER_REVIEW");
  const [selectedAllocationId, setSelectedAllocationId] = useState<
    string | null
  >(null);
  const [selectedDossier, setSelectedDossier] =
    useState<AdminReviewDossierSummary | null>(null);
  const [completedKind, setCompletedKind] = useState<
    "GENERIC" | "DOSSIER_REVIEW" | "ACTIVATED" | null
  >(null);
  const queryClient = useQueryClient();
  const allocations = useQuery({
    queryKey: ["work-allocations"],
    queryFn: () => workAllocationAdminApi.list({ pageSize: 50 }),
  });
  const reviewDossiers = useQuery({
    queryKey: ["review-dossiers", "allocation-composer"],
    queryFn: () => adminReviewApi.list({ pageSize: 100 }),
  });
  const unassignedDossiers = (reviewDossiers.data?.data ?? []).filter(
    (dossier) => dossier.assignmentCount === 0,
  );
  const staff = useQuery({
    queryKey: ["staff-accounts", "allocation-members"],
    queryFn: () =>
      staffAccountsApi.list({
        role: "MODERATOR",
        status: "ACTIVE",
        pageSize: 100,
      }),
  });
  const allocationDetail = useQuery({
    queryKey: ["work-allocation", selectedAllocationId],
    queryFn: () => workAllocationAdminApi.get(selectedAllocationId ?? ""),
    enabled: Boolean(selectedAllocationId),
  });
  const activateDraft = useMutation({
    mutationFn: (allocationId: string) =>
      workAllocationAdminApi.activate(allocationId, []),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["work-allocations"] });
      setCompletedKind("ACTIVATED");
    },
  });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["work-allocations"] }),
      queryClient.invalidateQueries({
        queryKey: ["review-dossiers", "allocation-composer"],
      }),
    ]);
    setIsCreating(false);
    setSelectedDossier(null);
  };
  const completeAssignment = async (kind: "GENERIC" | "DOSSIER_REVIEW") => {
    await refresh();
    setCompletedKind(kind);
  };

  return (
    <section
      aria-labelledby="work-allocations-title"
      className="mx-auto max-w-7xl space-y-6 pb-12"
    >
      <header className="rounded-2xl border border-neutral-800 bg-neutral-950 px-5 py-6 text-white sm:px-8 sm:py-7">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-primary-200">
              <ClipboardList aria-hidden="true" className="size-4" /> Điều phối
              công việc
            </div>
            <h1
              className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
              id="work-allocations-title"
            >
              Phân công công việc
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-300">
              Chọn tác phẩm đã nộp, giao người thẩm định và theo dõi tiến độ xử
              lý.
            </p>
          </div>
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary-400 px-5 text-sm font-bold text-neutral-950 transition hover:bg-primary-300 active:translate-y-px"
            onClick={() => {
              setCompletedKind(null);
              setSelectedDossier(null);
              setIsCreating((current) => !current);
            }}
            type="button"
          >
            <Plus aria-hidden="true" className="size-4" />
            {isCreating ? "Đóng biểu mẫu" : "Giao hồ sơ thẩm định"}
          </button>
        </div>
      </header>
      {completedKind ? (
        <WorkflowNextStep
          action={
            completedKind === "DOSSIER_REVIEW"
              ? { href: "/admin/reviews", label: "Theo dõi thẩm định" }
              : { href: "#allocation-list", label: "Theo dõi công việc" }
          }
          description={
            completedKind === "DOSSIER_REVIEW"
              ? "Người kiểm duyệt sẽ nhận hồ sơ trong hàng đợi. Theo dõi báo cáo trước khi ra quyết định cuối."
              : "Nhân viên sẽ thấy phân công trong không gian làm việc của họ. Theo dõi trạng thái và thời hạn trong danh sách bên dưới."
          }
          title={
            completedKind === "DOSSIER_REVIEW"
              ? "Đã giao hồ sơ thẩm định"
              : completedKind === "ACTIVATED"
                ? "Đã kích hoạt phân công"
                : "Đã giao công việc cho nhân viên"
          }
          tone="success"
        />
      ) : null}
      {reviewDossiers.isError ? (
        <div
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200"
          role="alert"
        >
          Chưa tải được hồ sơ chờ giao.{" "}
          <button
            className="font-bold underline"
            onClick={() => void reviewDossiers.refetch()}
            type="button"
          >
            Thử lại
          </button>
        </div>
      ) : null}
      {unassignedDossiers.length > 0 ? (
        <section
          className="rounded-2xl border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900"
          aria-label="Hồ sơ chờ phân công"
        >
          <h2 className="text-lg font-bold text-neutral-950 dark:text-white">
            Tác phẩm chờ giao thẩm định
          </h2>
          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">
            Chọn một hồ sơ để giao trực tiếp cho nhân viên.
          </p>
          <div className="mt-4 grid gap-2">
            {unassignedDossiers.slice(0, 5).map((dossier) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-neutral-200 p-3 dark:border-neutral-700"
                key={dossier.dossierId}
              >
                <div className="min-w-0">
                  <p className="font-bold text-neutral-950 dark:text-white">
                    {dossier.dossierTitle}
                  </p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-300">
                    {dossier.dossierCode} ·{" "}
                    {dossier.status === "SUBMITTED"
                      ? "Đã nộp"
                      : dossier.status === "PRECHECK"
                        ? "Đang kiểm tra"
                        : "Chờ giao người thẩm định"}
                  </p>
                </div>
                <button
                  className="min-h-10 rounded-lg bg-primary-700 px-4 text-sm font-bold text-white"
                  onClick={() => {
                    setCompletedKind(null);
                    setSelectedDossier(dossier);
                    setCreationKind("DOSSIER_REVIEW");
                    setIsCreating(true);
                  }}
                  type="button"
                >
                  Giao hồ sơ
                </button>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {isCreating ? (
        <section className="space-y-4" aria-label="Loại phân công">
          <div
            aria-label="Chọn loại phân công"
            className="inline-flex w-full gap-1 rounded-xl border border-neutral-200 bg-neutral-100 p-1 dark:border-neutral-800 dark:bg-neutral-950 sm:w-auto"
            role="tablist"
          >
            <button
              aria-selected={creationKind === "DOSSIER_REVIEW"}
              className={`min-h-10 flex-1 rounded-lg px-4 text-sm font-bold transition sm:flex-none ${
                creationKind === "DOSSIER_REVIEW"
                  ? "bg-white text-neutral-950 shadow-sm dark:bg-neutral-800 dark:text-white"
                  : "text-neutral-600 hover:text-neutral-950 dark:text-neutral-300 dark:hover:text-white"
              }`}
              onClick={() => setCreationKind("DOSSIER_REVIEW")}
              role="tab"
              type="button"
            >
              Hồ sơ thẩm định
            </button>
            <button
              aria-selected={creationKind === "GENERIC"}
              className={`min-h-10 flex-1 rounded-lg px-4 text-sm font-bold transition sm:flex-none ${
                creationKind === "GENERIC"
                  ? "bg-white text-neutral-950 shadow-sm dark:bg-neutral-800 dark:text-white"
                  : "text-neutral-600 hover:text-neutral-950 dark:text-neutral-300 dark:hover:text-white"
              }`}
              onClick={() => setCreationKind("GENERIC")}
              role="tab"
              type="button"
            >
              Công việc chung
            </button>
          </div>
          {creationKind === "GENERIC" ? (
            <GenericAllocationForm
              staff={staff.data?.data ?? []}
              onSaved={() => completeAssignment("GENERIC")}
            />
          ) : (
            <DossierAllocationForm
              key={selectedDossier?.dossierId ?? "manual"}
              initialDossier={selectedDossier ?? undefined}
              staff={staff.data?.data ?? []}
              onSaved={() => completeAssignment("DOSSIER_REVIEW")}
            />
          )}
        </section>
      ) : null}

      <section aria-label="Danh sách phân công" id="allocation-list">
        <WorkAllocationList
          isDetailError={allocationDetail.isError}
          isDetailPending={allocationDetail.isPending}
          isError={allocations.isError}
          isPending={allocations.isPending}
          onSelect={setSelectedAllocationId}
          onActivateDraft={(allocationId) => activateDraft.mutate(allocationId)}
          activatingDraftId={
            activateDraft.isPending ? activateDraft.variables : null
          }
          activationError={activateDraft.isError ? activateDraft.error : null}
          failedDraftId={activateDraft.isError ? activateDraft.variables : null}
          rows={allocations.data?.data ?? []}
          selectedAllocationId={selectedAllocationId}
          selectedDetail={allocationDetail.data ?? null}
        />
      </section>
    </section>
  );
}
