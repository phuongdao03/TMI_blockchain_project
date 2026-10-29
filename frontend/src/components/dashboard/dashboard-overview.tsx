"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FilePlus2, FolderKanban, LoaderCircle } from "lucide-react";
import Link from "next/link";

import {
  ApplicantTasks,
  dossierNextAction,
} from "@/components/dashboard/applicant-tasks";
import { DossierStatusBadge } from "@/components/dossiers/dossier-status";
import { ModeratorHrDashboardSummary } from "@/components/hr/moderator-hr-dashboard-summary";
import { RoleDashboardOverview } from "@/components/dashboard/role-dashboard-overview";
import { dossierApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { resolveWorkspacePersona } from "@/lib/auth/role-workspaces";
import { dossierKeys } from "@/lib/dossiers/query-keys";
import { ApplicantAccountSummary } from "./applicant-account-summary";

export function DashboardOverview() {
  const user = useAuthUser();
  const queryClient = useQueryClient();
  const persona = resolveWorkspacePersona(user?.roles ?? []);
  const isUser = persona === "USER";
  const filters = { page: 1, pageSize: 5 } as const;
  const dossiers = useQuery({
    queryKey: dossierKeys.list(filters),
    queryFn: () => dossierApi.list(filters),
    enabled: isUser,
    staleTime: 30_000,
  });
  if (!isUser) {
    const roleDashboard = (
      <RoleDashboardOverview
        accountType={user?.accountType}
        onUpgraded={(upgradedUser) => {
          queryClient.setQueryData(["auth", "me"], upgradedUser);
        }}
        persona={persona}
      />
    );
    if (persona === "MODERATOR") {
      return (
        <div className="mx-auto max-w-7xl space-y-8 pb-12">
          {roleDashboard}
          <ModeratorHrDashboardSummary />
        </div>
      );
    }
    return roleDashboard;
  }
  const visibleDossiers = dossiers.data?.data ?? [];
  const canCreateFirstDossier =
    !dossiers.isPending && !dossiers.isError && visibleDossiers.length === 0;

  return (
    <div className="dashboard-overview mx-auto max-w-7xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
            Trung tâm hồ sơ
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-[-0.04em] sm:text-4xl">
            Việc cần làm
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-neutral-600">
            Tiếp tục hồ sơ đang dở, theo dõi cập nhật mới nhất và nhận bằng xác
            lập khi hoàn tất.
          </p>
        </div>
        {!dossiers.isPending &&
        !dossiers.isError &&
        visibleDossiers.length > 0 ? (
          <Link
            className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-bold text-white"
            href="/dossiers/new"
          >
            <FilePlus2 aria-hidden="true" className="size-4" />
            Tạo hồ sơ mới
          </Link>
        ) : null}
      </header>

      <ApplicantTasks enabled={Boolean(dossiers.data?.meta.total)} />
      {user?.id ? <ApplicantAccountSummary userId={user.id} /> : null}
      {canCreateFirstDossier ? (
        <Link
          className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-bold text-white"
          href="/dossiers/new"
        >
          <FilePlus2 aria-hidden="true" className="size-4" />
          Tạo hồ sơ mới
        </Link>
      ) : dossiers.isError ? (
        <div
          role="alert"
          className="rounded-lg border border-[var(--theme-border)] p-4"
        >
          <p>Chưa thể tải hồ sơ của bạn. Vui lòng thử lại.</p>
          <button
            className="mt-2 min-h-11 font-bold underline"
            onClick={() => void dossiers.refetch()}
            type="button"
          >
            Tải lại danh sách
          </button>
        </div>
      ) : dossiers.isPending ? (
        <p role="status" className="text-sm text-[var(--theme-muted)]">
          Đang tải hồ sơ của bạn…
        </p>
      ) : null}

      {!dossiers.isPending &&
      !dossiers.isError &&
      visibleDossiers.length === 0 ? (
        <section
          aria-labelledby="first-dossier-title"
          className="dashboard-first-steps"
        >
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
              Trước khi gửi
            </p>
            <h2 className="mt-2 text-xl font-bold" id="first-dossier-title">
              Bắt đầu hồ sơ đầu tiên
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
              Bạn sẽ được hướng dẫn theo loại hồ sơ đang mở. Các trường và tài
              liệu cần chuẩn bị được hiển thị sau khi chọn loại.
            </p>
          </div>
          <ol className="mt-5 divide-y divide-[var(--theme-border)] border-y border-[var(--theme-border)] sm:grid sm:grid-cols-3 sm:divide-y-0">
            <li className="py-4 sm:pr-6">
              <strong className="text-sm">01 · Chọn loại hồ sơ phù hợp</strong>
              <p className="mt-1 text-sm text-[var(--theme-muted)]">
                Xem thông tin và tài liệu theo biểu mẫu hiện hành.
              </p>
            </li>
            <li className="py-4 sm:border-l sm:border-[var(--theme-border)] sm:px-6">
              <strong className="text-sm">
                02 · Lưu bản nháp và bổ sung tài liệu
              </strong>
              <p className="mt-1 text-sm text-[var(--theme-muted)]">
                Có thể quay lại để hoàn thiện trước khi gửi.
              </p>
            </li>
            <li className="py-4 sm:border-l sm:border-[var(--theme-border)] sm:pl-6">
              <strong className="text-sm">
                03 · Kiểm tra, gửi và theo dõi
              </strong>
              <p className="mt-1 text-sm text-[var(--theme-muted)]">
                Theo dõi trạng thái và yêu cầu bổ sung trong hồ sơ.
              </p>
            </li>
          </ol>
        </section>
      ) : (
        <>
          <section className="grid gap-5 xl:grid-cols-[1.45fr_0.55fr]">
            <section className="dashboard-surface overflow-hidden rounded-xl border">
              <header className="flex items-center justify-between border-b border-black/8 px-6 py-5">
                <div>
                  <h2 className="text-lg font-bold">Hồ sơ gần đây</h2>
                  <p className="mt-1 text-sm text-neutral-500">
                    Tiếp tục đúng nơi bạn đang dở.
                  </p>
                  {dossiers.data ? (
                    <p className="mt-1 text-sm text-[var(--theme-muted)]">
                      Tổng cộng {dossiers.data.meta.total} hồ sơ
                    </p>
                  ) : null}
                </div>
                <Link
                  className="text-sm font-bold text-primary-700 hover:text-primary-800"
                  href="/dossiers"
                >
                  Xem tất cả
                </Link>
              </header>
              <div>
                {dossiers.isPending ? (
                  <div className="space-y-3 px-6 py-5" role="status">
                    <p className="flex items-center gap-2 text-sm font-semibold text-neutral-500">
                      <LoaderCircle
                        aria-hidden="true"
                        className="thv-loading-spinner size-5"
                      />
                      Đang tải hồ sơ…
                    </p>
                    {[0, 1, 2].map((item) => (
                      <div
                        aria-hidden="true"
                        className="dashboard-skeleton h-14 animate-pulse rounded-lg"
                        key={item}
                      />
                    ))}
                  </div>
                ) : dossiers.isError ? (
                  <div className="flex min-h-44 flex-col items-center justify-center px-6 text-center">
                    <p className="font-bold text-neutral-900">
                      Chưa thể tải hồ sơ
                    </p>
                    <p className="mt-1 max-w-sm text-sm leading-6 text-neutral-500">
                      Vui lòng kiểm tra kết nối và thử tải lại trang để tiếp
                      tục.
                    </p>
                    <button
                      className="mt-4 min-h-11 rounded-xl border border-neutral-300 px-4 text-sm font-bold"
                      onClick={() => void dossiers.refetch()}
                      type="button"
                    >
                      Thử lại
                    </button>
                  </div>
                ) : dossiers.data?.data.length ? (
                  <div className="divide-y divide-neutral-100">
                    {dossiers.data.data.slice(0, 3).map((dossier) => (
                      <Link
                        className="flex min-h-20 flex-col items-start justify-center gap-2.5 px-4 py-4 hover:bg-neutral-50 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6"
                        href={`/dossiers/${dossier.id}`}
                        key={dossier.id}
                      >
                        <div className="min-w-0 max-w-full">
                          <p className="break-words text-base font-bold">
                            {dossier.title}
                          </p>
                          <p className="mt-1 text-sm text-[var(--theme-muted)]">
                            {dossier.code} · Cập nhật{" "}
                            {new Date(dossier.updatedAt).toLocaleDateString(
                              "vi-VN",
                            )}
                          </p>
                          <p className="mt-2 text-sm font-semibold text-[var(--theme-accent)]">
                            {dossierNextAction(dossier.status)} →
                          </p>
                        </div>
                        <DossierStatusBadge
                          className="shrink-0 whitespace-nowrap"
                          status={dossier.status}
                        />
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="flex min-h-44 flex-col items-center justify-center px-6 text-center">
                    <FolderKanban
                      aria-hidden="true"
                      className="size-7 text-neutral-400"
                    />
                    <p className="mt-3 font-bold">Chưa có hồ sơ</p>
                    <p className="mt-1 text-sm text-neutral-500">
                      Tạo hồ sơ đầu tiên để bắt đầu.
                    </p>
                  </div>
                )}
              </div>
            </section>

            <nav
              aria-label="Dịch vụ và tài khoản"
              className="border-t border-[var(--theme-border)] py-5 xl:border-t-0 xl:border-l xl:px-6"
            >
              <h2 className="text-lg font-bold">Truy cập nhanh</h2>
              <div className="mt-3 divide-y divide-[var(--theme-border)]">
                {[
                  { href: "/wallet", label: "Ví và lịch sử giao dịch" },
                  { href: "/notifications", label: "Thông báo của tôi" },
                  { href: "/advertising", label: "Quảng bá hồ sơ" },
                  { href: "/membership", label: "Hội viên và quyền lợi" },
                  { href: "/community", label: "Khám phá cộng đồng" },
                ].map((item) => (
                  <Link
                    className="flex min-h-12 items-center justify-between gap-3 py-3 text-sm font-semibold"
                    href={item.href}
                    key={item.href}
                  >
                    {item.label}
                    <span aria-hidden="true">→</span>
                  </Link>
                ))}
              </div>
            </nav>
          </section>
        </>
      )}
    </div>
  );
}
