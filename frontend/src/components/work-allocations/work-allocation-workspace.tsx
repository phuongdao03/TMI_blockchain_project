"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, Plus } from "lucide-react";
import { useState } from "react";

import { DossierAllocationForm } from "@/components/work-allocations/dossier-allocation-form";
import { GenericAllocationForm } from "@/components/work-allocations/generic-allocation-form";
import { WorkAllocationList } from "@/components/work-allocations/work-allocation-list";
import { staffAccountsApi, workAllocationAdminApi } from "@/lib/api/client";

export function WorkAllocationWorkspace() {
  const [isCreating, setIsCreating] = useState(false);
  const [creationKind, setCreationKind] = useState<
    "GENERIC" | "DOSSIER_REVIEW"
  >("GENERIC");
  const [selectedAllocationId, setSelectedAllocationId] = useState<
    string | null
  >(null);
  const queryClient = useQueryClient();
  const allocations = useQuery({
    queryKey: ["work-allocations"],
    queryFn: () => workAllocationAdminApi.list({ pageSize: 50 }),
  });
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
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["work-allocations"] });
    setIsCreating(false);
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
              Phân chia trách nhiệm rõ ràng cho công việc và hồ sơ có nhiều tài
              liệu, có thể kiểm tra lại tiến độ và phạm vi đã giao.
            </p>
          </div>
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary-400 px-5 text-sm font-bold text-neutral-950 transition hover:bg-primary-300 active:translate-y-px"
            onClick={() => setIsCreating((current) => !current)}
            type="button"
          >
            <Plus aria-hidden="true" className="size-4" />
            {isCreating ? "Đóng biểu mẫu" : "Tạo phân công"}
          </button>
        </div>
      </header>

      {isCreating ? (
        <section className="space-y-4" aria-label="Loại phân công">
          <div
            aria-label="Chọn loại phân công"
            className="inline-flex w-full gap-1 rounded-xl border border-neutral-200 bg-neutral-100 p-1 dark:border-neutral-800 dark:bg-neutral-950 sm:w-auto"
            role="tablist"
          >
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
          </div>
          {creationKind === "GENERIC" ? (
            <GenericAllocationForm
              staff={staff.data?.data ?? []}
              onSaved={refresh}
            />
          ) : (
            <DossierAllocationForm
              staff={staff.data?.data ?? []}
              onSaved={refresh}
            />
          )}
        </section>
      ) : null}

      <section aria-label="Danh sách phân công">
        <WorkAllocationList
          isDetailError={allocationDetail.isError}
          isDetailPending={allocationDetail.isPending}
          isError={allocations.isError}
          isPending={allocations.isPending}
          onSelect={setSelectedAllocationId}
          rows={allocations.data?.data ?? []}
          selectedAllocationId={selectedAllocationId}
          selectedDetail={allocationDetail.data ?? null}
        />
      </section>
    </section>
  );
}
