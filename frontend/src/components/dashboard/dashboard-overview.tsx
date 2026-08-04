"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BadgeCheck,
  Blocks,
  FileCheck2,
  FilePlus2,
  FolderKanban,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { DossierStatusBadge } from "@/components/dossiers/dossier-status";
import { RoleDashboardOverview } from "@/components/dashboard/role-dashboard-overview";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dossierApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { resolveWorkspacePersona } from "@/lib/auth/role-workspaces";
import { dossierKeys } from "@/lib/dossiers/query-keys";

export function DashboardOverview() {
  const user = useAuthUser();
  const persona = resolveWorkspacePersona(user?.roles ?? []);
  const isApplicant = persona === "APPLICANT";
  const filters = { page: 1, pageSize: 5 } as const;
  const dossiers = useQuery({
    queryKey: dossierKeys.list(filters),
    queryFn: () => dossierApi.list(filters),
    enabled: isApplicant,
  });
  if (!isApplicant) {
    return <RoleDashboardOverview persona={persona} roles={user?.roles} />;
  }
  const total = dossiers.data?.meta.total ?? 0;
  const submitted =
    dossiers.data?.data.filter(({ status }) => status !== "DRAFT").length ?? 0;

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
            Không gian làm việc
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            Tổng quan xác lập
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
            Một điểm theo dõi hồ sơ, phiên bản và bằng chứng xác minh của bạn.
          </p>
        </div>
        <Link
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary-600 px-5 text-sm font-bold text-white shadow-lg shadow-primary-950/15 hover:bg-primary-700"
          href="/ho-so/tao-moi"
        >
          <FilePlus2 aria-hidden="true" className="size-4" />
          Tạo hồ sơ mới
        </Link>
      </div>

      <section className="hero-grid-surface relative overflow-hidden rounded-3xl border border-white/5 bg-ink-950 px-6 py-8 text-white shadow-2xl shadow-slate-950/10 sm:px-8 lg:grid lg:grid-cols-[1fr_auto] lg:items-end lg:gap-10 lg:py-10">
        <div className="relative z-10 max-w-3xl">
          <span className="mb-5 grid size-12 place-items-center rounded-2xl border border-gold-300/30 bg-gold-300/10 text-gold-300">
            <ShieldCheck aria-hidden="true" className="size-6" />
          </span>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
            TMI Trust Workspace
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-[-0.02em] sm:text-3xl">
            Biến hồ sơ thành bằng chứng có thể kiểm chứng.
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
            Chuẩn hóa thông tin, khóa mỗi lần nộp thành snapshot và sẵn sàng cho
            quy trình thẩm định.
          </p>
        </div>
        <Link
          className="relative z-10 mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 text-sm font-bold text-white hover:bg-white/10 lg:mt-0"
          href="/ho-so"
        >
          Mở không gian hồ sơ
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </section>

      <section
        aria-label="Chỉ số tổng quan"
        className="grid gap-4 md:grid-cols-3"
      >
        {[
          {
            label: "Tổng hồ sơ",
            value: dossiers.isPending ? "—" : String(total),
            detail: "Hồ sơ trong phạm vi của bạn",
            icon: FolderKanban,
          },
          {
            label: "Đã nộp",
            value: dossiers.isPending ? "—" : String(submitted),
            detail: "Có ít nhất một phiên bản bất biến",
            icon: FileCheck2,
          },
          {
            label: "Blockchain",
            value: "Sẵn sàng",
            detail: "Hạ tầng bằng chứng cho chứng thư hợp lệ",
            icon: Blocks,
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label}>
              <CardHeader className="flex-row items-start justify-between space-y-0">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-neutral-400">
                    {item.label}
                  </p>
                  <CardTitle className="mt-3 text-3xl">{item.value}</CardTitle>
                </div>
                <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary-700">
                  <Icon aria-hidden="true" className="size-5" />
                </span>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-neutral-500">
                  {item.detail}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="overflow-hidden">
          <CardHeader className="flex-row items-center justify-between border-b border-neutral-100">
            <div>
              <CardTitle>Hồ sơ gần đây</CardTitle>
              <p className="mt-1 text-sm text-neutral-500">
                Tiếp tục đúng nơi bạn đang dở.
              </p>
            </div>
            <Link
              className="text-sm font-bold text-primary-700 hover:text-primary-800"
              href="/ho-so"
            >
              Xem tất cả
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {dossiers.isPending ? (
              <div
                className="flex min-h-44 items-center justify-center gap-3 text-sm font-semibold text-neutral-500"
                role="status"
              >
                <LoaderCircle
                  aria-hidden="true"
                  className="size-5 animate-spin"
                />
                Đang tải hồ sơ…
              </div>
            ) : dossiers.isError ? (
              <div className="flex min-h-44 flex-col items-center justify-center px-6 text-center">
                <p className="font-bold text-neutral-900">Chưa thể tải hồ sơ</p>
                <p className="mt-1 max-w-sm text-sm leading-6 text-neutral-500">
                  Vui lòng kiểm tra kết nối và thử tải lại trang để tiếp tục.
                </p>
              </div>
            ) : dossiers.data?.data.length ? (
              <div className="divide-y divide-neutral-100">
                {dossiers.data.data.slice(0, 3).map((dossier) => (
                  <Link
                    className="flex min-h-20 items-center justify-between gap-4 px-6 py-4 hover:bg-neutral-50"
                    href={`/ho-so/${dossier.id}`}
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
          </CardContent>
        </Card>

        <Card className="border-gold-300/30 bg-amber-50/50">
          <CardHeader>
            <BadgeCheck aria-hidden="true" className="size-6 text-amber-700" />
            <CardTitle>Nền tảng tin cậy</CardTitle>
            <p className="text-sm leading-6 text-neutral-500">
              Mỗi phiên bản hồ sơ được chuẩn hóa cho chuỗi xác minh tiếp theo.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {["Toàn vẹn dữ liệu", "Dấu thời gian", "Xác minh công khai"].map(
              (label) => (
                <p
                  className="flex items-center gap-2 text-sm font-bold text-neutral-700"
                  key={label}
                >
                  <BadgeCheck
                    aria-hidden="true"
                    className="size-4 text-emerald-600"
                  />
                  {label}
                </p>
              ),
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
