"use client";

import { useQueries } from "@tanstack/react-query";
import Link from "next/link";

import { DossierStatusBadge } from "@/components/dossiers/dossier-status";
import { dossierApi } from "@/lib/api/client";
import type { DossierStatus } from "@/lib/api/types";
import { dossierKeys } from "@/lib/dossiers/query-keys";

const priorities = ["NEEDS_SUPPLEMENT", "PAYMENT_PENDING", "DRAFT"] as const;

export function dossierNextAction(status: DossierStatus) {
  if (status === "NEEDS_SUPPLEMENT") return "Bổ sung tài liệu được yêu cầu";
  if (status === "PAYMENT_PENDING") return "Xem khoản phí và thanh toán";
  if (status === "DRAFT") return "Tiếp tục hoàn thiện hồ sơ";
  if (status === "CERTIFICATE_ISSUED" || status === "PUBLISHED")
    return "Xem hồ sơ và bằng xác lập";
  if (status === "REJECTED") return "Xem kết quả và lý do";
  if (status === "REVOKED" || status === "CANCELLED")
    return "Xem chi tiết hồ sơ";
  return "Xem tiến độ hồ sơ";
}

export function ApplicantTasks({ enabled = true }: { enabled?: boolean }) {
  const queries = useQueries({
    queries: priorities.map((status) => {
      const filters = { page: 1, pageSize: 3, status };
      return {
        queryKey: dossierKeys.list(filters),
        queryFn: () => dossierApi.list(filters),
        staleTime: 30_000,
        enabled,
      };
    }),
  });
  const failed = queries.some((query) => query.isError);
  const pending = queries.some((query) => query.isPending);
  // Wait for every priority before presenting a complete, stable task order.
  const tasks = queries
    .flatMap((query) => query.data?.data ?? [])
    .filter(
      (task, index, all) => all.findIndex(({ id }) => id === task.id) === index,
    )
    .slice(0, 3);

  if (!enabled) return null;

  if (pending)
    return (
      <p className="py-3 text-sm text-[var(--theme-muted)]" role="status">
        Đang kiểm tra việc cần làm…
      </p>
    );
  if (failed)
    return (
      <div
        className="rounded-lg border border-[var(--theme-border)] p-4"
        role="alert"
      >
        <p className="text-sm">
          Chưa tải đủ việc cần làm. Bạn vẫn có thể xem hồ sơ bên dưới.
        </p>
        <button
          className="mt-2 min-h-11 text-sm font-bold underline underline-offset-4"
          onClick={() => {
            queries.forEach((query) => void query.refetch());
          }}
          type="button"
        >
          Tải lại việc cần làm
        </button>
      </div>
    );
  if (!tasks.length) return null;

  return (
    <section
      aria-labelledby="applicant-tasks-title"
      className="border-y border-[var(--theme-border)] py-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-bold" id="applicant-tasks-title">
          Cần bạn xử lý
        </h2>
        <p className="text-sm text-[var(--theme-muted)]">
          Ưu tiên bổ sung và thanh toán
        </p>
      </div>
      <ul className="mt-3 divide-y divide-[var(--theme-border)]">
        {tasks.map((task) => (
          <li key={task.id}>
            <Link
              className="flex min-h-20 flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between"
              href={`/dossiers/${task.id}`}
            >
              <div className="min-w-0">
                <p className="break-words font-semibold">{task.title}</p>
                <p className="mt-1 text-sm text-[var(--theme-muted)]">
                  {task.code}
                </p>
                <p className="mt-2 text-sm font-semibold text-[var(--theme-accent)]">
                  {dossierNextAction(task.status)} →
                </p>
              </div>
              <DossierStatusBadge
                className="self-start sm:shrink-0"
                status={task.status}
              />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
