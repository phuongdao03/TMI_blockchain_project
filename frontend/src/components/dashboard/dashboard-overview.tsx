"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BadgeCheck,
  CircleAlert,
  Clock3,
  FilePlus2,
  FolderKanban,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { DossierStatusBadge } from "@/components/dossiers/dossier-status";
import { RoleDashboardOverview } from "@/components/dashboard/role-dashboard-overview";
import { dossierApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { resolveWorkspacePersona } from "@/lib/auth/role-workspaces";
import { dossierKeys } from "@/lib/dossiers/query-keys";
import type { Dossier, DossierStatus } from "@/lib/api/types";

const attentionStatuses = new Set<DossierStatus>([
  "DRAFT",
  "NEEDS_SUPPLEMENT",
  "PAYMENT_PENDING",
]);
const completedStatuses = new Set<DossierStatus>([
  "CERTIFICATE_ISSUED",
  "PUBLISHED",
]);
const closedStatuses = new Set<DossierStatus>([
  ...completedStatuses,
  "REJECTED",
  "REVOKED",
  "CANCELLED",
]);

function nextAction(dossier: Dossier) {
  if (dossier.status === "DRAFT") {
    return {
      label: "Tiếp tục hoàn thiện hồ sơ",
      href: `/dossiers/${dossier.id}`,
    };
  }
  if (dossier.status === "NEEDS_SUPPLEMENT") {
    return {
      label: "Bổ sung tài liệu được yêu cầu",
      href: `/dossiers/${dossier.id}`,
    };
  }
  if (dossier.status === "PAYMENT_PENDING") {
    return {
      label: "Thanh toán phí phát hành",
      href: `/dossiers/${dossier.id}`,
    };
  }
  if (completedStatuses.has(dossier.status)) {
    return { label: "Tải chứng thư", href: "/certificates" };
  }
  return { label: "Xem tiến độ hồ sơ", href: `/dossiers/${dossier.id}` };
}

export function DashboardOverview() {
  const user = useAuthUser();
  const queryClient = useQueryClient();
  const [upgradeCompleted, setUpgradeCompleted] = useState(false);
  const persona = resolveWorkspacePersona(user?.roles ?? []);
  const isUser = persona === "USER";
  const filters = { page: 1, pageSize: 5 } as const;
  const dossiers = useQuery({
    queryKey: dossierKeys.list(filters),
    queryFn: () => dossierApi.list(filters),
    enabled: isUser,
  });
  if (!isUser) {
    return (
      <RoleDashboardOverview
        accountType={user?.accountType}
        onUpgraded={(upgradedUser) => {
          queryClient.setQueryData(["auth", "me"], upgradedUser);
          setUpgradeCompleted(true);
        }}
        persona={persona}
      />
    );
  }
  const visibleDossiers = dossiers.data?.data ?? [];
  const processingCount = visibleDossiers.filter(
    ({ status }) => status !== "DRAFT" && !closedStatuses.has(status),
  ).length;
  const attentionCount = visibleDossiers.filter(({ status }) =>
    attentionStatuses.has(status),
  ).length;
  const certificateCount = visibleDossiers.filter(({ status }) =>
    completedStatuses.has(status),
  ).length;
  const primaryDossier =
    visibleDossiers.find(({ status }) => attentionStatuses.has(status)) ??
    visibleDossiers[0];
  const primaryAction = primaryDossier ? nextAction(primaryDossier) : null;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header>
        <div>
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
            Trung tâm hồ sơ
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">
            Việc cần làm
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-neutral-600">
            Tiếp tục hồ sơ đang dở, theo dõi cập nhật mới nhất và nhận chứng thư
            khi hoàn tất.
          </p>
        </div>
      </header>

      {upgradeCompleted ? (
        <div
          className="dashboard-success-state rounded-xl border px-5 py-4 text-sm"
          role="status"
        >
          <p className="font-bold">Bạn đã có thể bắt đầu hồ sơ.</p>
          <p className="mt-1">
            Hoàn thiện thông tin liên hệ trước khi tải tài liệu lên.
          </p>
        </div>
      ) : null}

      <section className="hero-grid-surface relative overflow-hidden rounded-2xl border border-white/8 bg-neutral-950 px-6 py-8 text-white shadow-[0_24px_70px_rgb(15_15_15/0.16)] sm:px-8 lg:grid lg:min-h-72 lg:grid-cols-[1fr_auto] lg:items-end lg:gap-12 lg:px-10 lg:py-10">
        <div className="relative z-10 max-w-3xl">
          <span className="mb-7 grid size-11 place-items-center rounded-lg border border-gold-300/30 bg-gold-300/10 text-gold-300">
            {primaryDossier && attentionStatuses.has(primaryDossier.status) ? (
              <CircleAlert aria-hidden="true" className="size-6" />
            ) : (
              <Clock3 aria-hidden="true" className="size-6" />
            )}
          </span>
          <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-gold-300">
            {primaryDossier ? "Ưu tiên tiếp theo" : "Bắt đầu hồ sơ đầu tiên"}
          </p>
          <h2 className="mt-3 text-2xl font-bold tracking-[-0.03em] sm:text-3xl lg:text-4xl">
            {primaryDossier
              ? primaryAction?.label
              : "Chuẩn bị thông tin tài sản của bạn"}
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-300">
            {primaryDossier
              ? `${primaryDossier.title} · Cập nhật ${new Date(primaryDossier.updatedAt).toLocaleDateString("vi-VN")}`
              : "Bạn có thể lưu bản nháp và quay lại hoàn thiện bất cứ lúc nào."}
          </p>
        </div>
        <Link
          className="relative z-10 mt-8 inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-bold text-white shadow-lg shadow-black/20 hover:bg-primary-500 lg:mt-0"
          href={primaryAction?.href ?? "/dossiers/new"}
        >
          {!primaryAction ? (
            <FilePlus2 aria-hidden="true" className="size-4" />
          ) : null}
          {primaryAction?.label ?? "Tạo hồ sơ mới"}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </section>

      <section
        aria-label="Chỉ số tổng quan"
        className="dashboard-surface grid overflow-hidden rounded-xl border md:grid-cols-3"
      >
        {[
          {
            label: "Việc cần làm",
            value: dossiers.isPending ? "—" : String(attentionCount),
            detail: "Hồ sơ cần bạn hoàn thiện, bổ sung hoặc thanh toán",
            icon: FolderKanban,
          },
          {
            label: "Đang xử lý",
            value: dossiers.isPending ? "—" : String(processingCount),
            detail: "Hồ sơ đã gửi và đang được TMI xử lý",
            icon: Clock3,
          },
          {
            label: "Chứng thư sẵn sàng",
            value: dossiers.isPending ? "—" : String(certificateCount),
            detail: "Chứng thư đã phát hành và có thể tải xuống",
            icon: BadgeCheck,
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <article
              className="relative border-b border-black/8 p-6 last:border-b-0 md:border-r md:border-b-0 md:last:border-r-0"
              key={item.label}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-[0.62rem] font-bold uppercase tracking-[0.16em] text-neutral-500">
                    {item.label}
                  </p>
                  <p className="mt-3 text-4xl font-bold tracking-[-0.04em]">
                    {item.value}
                  </p>
                </div>
                <span className="grid size-9 place-items-center rounded-lg border border-primary-100 bg-primary-50 text-primary-700">
                  <Icon aria-hidden="true" className="size-5" />
                </span>
              </div>
              <p className="mt-5 max-w-xs text-sm leading-6 text-neutral-600">
                {item.detail}
              </p>
            </article>
          );
        })}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.45fr_0.55fr]">
        <section className="dashboard-surface overflow-hidden rounded-xl border">
          <header className="flex items-center justify-between border-b border-black/8 px-6 py-5">
            <div>
              <h2 className="text-lg font-bold">Hồ sơ gần đây</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Tiếp tục đúng nơi bạn đang dở.
              </p>
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
                <span className="sr-only">Đang tải hồ sơ…</span>
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
                <p className="font-bold text-neutral-900">Chưa thể tải hồ sơ</p>
                <p className="mt-1 max-w-sm text-sm leading-6 text-neutral-500">
                  Vui lòng kiểm tra kết nối và thử tải lại trang để tiếp tục.
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
                    className="flex min-h-20 items-center justify-between gap-4 px-6 py-4 hover:bg-neutral-50"
                    href={`/dossiers/${dossier.id}`}
                    key={dossier.id}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold">
                        {dossier.title}
                      </p>
                      <p className="mt-1 font-mono text-[0.68rem] text-neutral-400">
                        {dossier.code}
                      </p>
                    </div>
                    <DossierStatusBadge status={dossier.status} />
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

        <section className="rounded-xl border border-white/10 bg-neutral-950 p-6 text-white">
          <div>
            <BadgeCheck aria-hidden="true" className="size-6 text-gold-300" />
            <h2 className="mt-6 text-lg font-bold">Cập nhật gần nhất</h2>
            <p className="text-sm leading-6 text-slate-300">
              Theo dõi những thay đổi quan trọng của hồ sơ.
            </p>
          </div>
          <div className="mt-6 space-y-3 border-t border-white/10 pt-5">
            {[
              "Trạng thái dễ hiểu",
              "Thông báo khi cần bổ sung",
              "Chứng thư sẵn sàng để tải",
            ].map((label) => (
              <p
                className="flex items-center gap-2 text-sm font-semibold text-slate-300"
                key={label}
              >
                <BadgeCheck
                  aria-hidden="true"
                  className="size-4 text-gold-300"
                />
                {label}
              </p>
            ))}
          </div>
        </section>
      </section>
    </div>
  );
}
