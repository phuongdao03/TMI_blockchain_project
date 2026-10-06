"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  BookOpenText,
  ExternalLink,
  FilePenLine,
  Search,
} from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { adminCertificateApi } from "@/lib/api/client";
import { CertificateContentDrafts } from "@/components/admin/certificate-content-drafts";
import type { CertificateStatus, PublicationStatus } from "@/lib/api/types";
import { displayCnsDossierCode } from "@/lib/brand/identifiers";

const pageSize = 10;

const statusLabels: Record<CertificateStatus, string> = {
  ACTIVE: "Có hiệu lực",
  EXPIRED: "Hết hiệu lực",
  REVOKED: "Đã thu hồi",
};

const publicationLabels: Record<PublicationStatus, string> = {
  DRAFT: "Bản nháp",
  PENDING_PUBLICATION: "Chờ công bố",
  PUBLISHED: "Đang công bố",
  HIDDEN: "Đã ẩn",
  SUSPENDED: "Tạm ngưng",
  ARCHIVED: "Đã lưu trữ",
};

export function AdminCertificateManager() {
  const queryClient = useQueryClient();
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CertificateStatus | "">("");
  const [publicationStatus, setPublicationStatus] = useState<
    PublicationStatus | ""
  >("");
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: [
      "admin",
      "certificates",
      search,
      status,
      publicationStatus,
      page,
    ],
    queryFn: () =>
      adminCertificateApi.list({
        page,
        pageSize,
        search: search || undefined,
        status: status || undefined,
        publicationStatus: publicationStatus || undefined,
      }),
  });

  const listing = useMutation({
    mutationFn: (input: {
      id: string;
      expectedWorkVersion: number;
      showCertificate: boolean;
    }) =>
      adminCertificateApi.configureListing(input.id, {
        expectedWorkVersion: input.expectedWorkVersion,
        showCertificate: input.showCertificate,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin", "certificates"] }),
        queryClient.invalidateQueries({
          queryKey: ["admin", "public-work-preview"],
        }),
        queryClient.invalidateQueries({ queryKey: ["admin", "public-work"] }),
      ]);
    },
  });

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
    setPage(1);
  }

  const total = query.data?.meta.total ?? 0;

  return (
    <main className="mx-auto max-w-7xl space-y-6 pb-8">
      <CertificateContentDrafts />
      <header className="flex flex-col gap-5 border-b border-neutral-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-primary-700">
            <BadgeCheck className="size-4" aria-hidden="true" /> Hồ sơ xác minh
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
            Quản lý bằng xác lập
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
            Tra cứu bằng xác lập đã cấp, kiểm soát nơi hiển thị và theo dõi
            phiên bản. Bằng xác lập thu hồi vẫn giữ trang xác minh và lịch sử để
            đối chiếu.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl border border-primary-700 bg-white px-4 text-sm font-bold text-primary-700 hover:bg-primary-50"
            href="/admin/certificates/corrections"
          >
            <FilePenLine className="size-4" aria-hidden="true" /> Sửa bằng đã
            cấp
          </Link>
          <Link
            className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl border border-neutral-300 bg-white px-4 text-sm font-bold text-neutral-800 hover:bg-neutral-50"
            href="/admin/content"
          >
            <BookOpenText className="size-4" aria-hidden="true" /> Nội dung công
            bố
          </Link>
        </div>
      </header>

      <section
        aria-label="Tìm và lọc bằng xác lập"
        className="rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5"
      >
        <form
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={submitSearch}
        >
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Tìm bằng xác lập</span>
            <Search
              aria-hidden="true"
              className="absolute left-3 top-3.5 size-4 text-neutral-500"
            />
            <input
              className="min-h-11 w-full rounded-xl border border-neutral-300 bg-white pl-10 pr-3 text-sm"
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Số bằng xác lập, mã hồ sơ hoặc tên tác phẩm"
              type="search"
              value={searchDraft}
            />
          </label>
          <button
            className="min-h-11 rounded-xl bg-primary-700 px-5 text-sm font-bold text-white"
            type="submit"
          >
            Tìm bằng xác lập
          </button>
        </form>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-xs font-bold text-neutral-700">
            Trạng thái bằng xác lập
            <select
              aria-label="Lọc trạng thái bằng xác lập"
              className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm font-semibold"
              onChange={(event) => {
                setStatus(event.target.value as CertificateStatus | "");
                setPage(1);
              }}
              value={status}
            >
              <option value="">Tất cả trạng thái</option>
              {Object.entries(statusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-bold text-neutral-700">
            Trạng thái nội dung công bố
            <select
              aria-label="Lọc trạng thái công bố"
              className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm font-semibold"
              onChange={(event) => {
                setPublicationStatus(
                  event.target.value as PublicationStatus | "",
                );
                setPage(1);
              }}
              value={publicationStatus}
            >
              <option value="">Tất cả nội dung</option>
              {Object.entries(publicationLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="mt-4 text-sm text-neutral-600" role="status">
          {query.isPending
            ? "Đang tải bằng xác lập…"
            : `${total} bằng xác lập phù hợp`}
        </p>
      </section>

      {query.isError ? (
        <div
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          role="alert"
        >
          Không thể tải bằng xác lập.{" "}
          <button
            className="font-bold underline"
            onClick={() => void query.refetch()}
            type="button"
          >
            Thử lại
          </button>
        </div>
      ) : null}
      {query.data && query.data.data.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-neutral-300 bg-white p-8 text-center text-sm text-neutral-600">
          Không có bằng xác lập phù hợp. Thử đổi từ khóa hoặc bộ lọc.
        </div>
      ) : null}

      {query.data && query.data.data.length > 0 ? (
        <section
          aria-label="Danh sách bằng xác lập"
          className="divide-y divide-neutral-200 overflow-hidden rounded-2xl border border-neutral-200 bg-white"
        >
          {query.data.data.map((item) => {
            const certificate = item.certificate;
            const visibility =
              certificate.status === "REVOKED"
                ? "Đã thu hồi · chỉ tra cứu"
                : item.isDiscoverable
                  ? "Trong danh mục công khai"
                  : "Chỉ tra cứu trực tiếp";

            return (
              <article className="p-4 sm:p-5" key={certificate.id}>
                <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
                  <span className="font-mono text-primary-700">
                    {certificate.certificateNumber}
                  </span>
                  <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-neutral-800">
                    {statusLabels[certificate.status]}
                  </span>
                  <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-amber-900">
                    {visibility}
                  </span>
                </div>
                <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <h2 className="text-lg font-bold text-neutral-950">
                      {certificate.assetTitle}
                    </h2>
                    <p className="mt-1 text-sm text-neutral-600">
                      {displayCnsDossierCode(certificate.dossierCode)} · Phiên
                      bản {certificate.currentVersionNo}
                    </p>
                    <p className="mt-1 text-xs text-neutral-500">
                      Nội dung:{" "}
                      {item.publicationStatus
                        ? publicationLabels[item.publicationStatus]
                        : "Chưa có bản công bố"}
                    </p>
                    {item.publicationStatus !== "PUBLISHED" ? (
                      <p className="mt-1 text-xs text-neutral-600">
                        Tác phẩm chưa công bố; thay đổi hiển thị không tự đưa
                        bằng xác lập vào danh mục công khai.
                      </p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link
                      aria-label={`Xác minh ${certificate.certificateNumber}`}
                      className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-neutral-950 px-3 text-sm font-bold text-white"
                      href={`/verify/${encodeURIComponent(certificate.certificateNumber)}`}
                    >
                      Xác minh{" "}
                      <ExternalLink className="size-4" aria-hidden="true" />
                    </Link>
                    {item.publicWorkId ? (
                      <Link
                        className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800 hover:bg-neutral-50"
                        href={`/admin/publications/${item.publicWorkId}`}
                      >
                        Nội dung công bố{" "}
                        <FilePenLine className="size-4" aria-hidden="true" />
                      </Link>
                    ) : null}
                  </div>
                </div>
                <details className="mt-4 border-t border-neutral-200 pt-3">
                  <summary className="cursor-pointer text-sm font-bold text-primary-700">
                    Quản lý hiển thị và phiên bản
                  </summary>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {item.publicWorkId &&
                    item.publicWorkVersion != null &&
                    certificate.status === "ACTIVE" ? (
                      <button
                        aria-pressed={item.showCertificate ?? true}
                        className="min-h-10 rounded-lg border border-primary-200 bg-primary-50 px-3 text-sm font-bold text-primary-800 disabled:opacity-50"
                        disabled={listing.isPending}
                        onClick={() =>
                          listing.mutate({
                            id: certificate.id,
                            expectedWorkVersion: item.publicWorkVersion!,
                            showCertificate: !(item.showCertificate ?? true),
                          })
                        }
                        type="button"
                      >
                        {(item.showCertificate ?? true)
                          ? "Ẩn khỏi trang tác phẩm"
                          : "Cho hiển thị cùng tác phẩm"}
                      </button>
                    ) : null}
                    {certificate.status === "ACTIVE" ? (
                      <Link
                        className="inline-flex min-h-10 items-center rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800"
                        href={`/certificates/${certificate.id}#certificate-update`}
                      >
                        Tạo phiên bản điều chỉnh
                      </Link>
                    ) : null}
                    {certificate.status === "ACTIVE" &&
                    certificate.certificateNumber.startsWith("THV-") &&
                    certificate.blockchainStatus === "CONFIRMED" &&
                    certificate.transactionHash ? (
                      <Link
                        className="min-h-10 rounded-lg border border-[#b7882f] px-3 text-sm font-bold text-[#720b17]"
                        href={`/admin/certificates/corrections/${encodeURIComponent(certificate.id)}`}
                      >
                        Chỉnh nội dung bằng cũ
                      </Link>
                    ) : null}
                    <Link
                      className="inline-flex min-h-10 items-center rounded-lg border border-neutral-300 px-3 text-sm font-bold text-neutral-800"
                      href={`/certificates/${certificate.id}`}
                    >
                      Lịch sử phiên bản
                    </Link>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-neutral-600">
                    Thay đổi hiển thị không tự công bố tác phẩm; bằng xác lập
                    vẫn tra cứu bằng số hoặc liên kết trực tiếp.
                  </p>
                  {listing.variables?.id === certificate.id &&
                  listing.isError ? (
                    <p className="mt-2 text-sm text-red-800" role="alert">
                      Chưa lưu được lựa chọn. Tải lại danh sách nếu dữ liệu vừa
                      thay đổi.
                    </p>
                  ) : null}
                  {listing.variables?.id === certificate.id &&
                  listing.isSuccess ? (
                    <p className="mt-2 text-sm text-emerald-800" role="status">
                      Đã lưu lựa chọn hiển thị bằng xác lập.
                    </p>
                  ) : null}
                </details>
              </article>
            );
          })}
        </section>
      ) : null}

      {query.data && total > pageSize ? (
        <nav
          aria-label="Trang bằng xác lập"
          className="flex items-center justify-between gap-3 text-sm font-semibold text-neutral-700"
        >
          <button
            className="min-h-10 rounded-lg border border-neutral-300 px-4 disabled:opacity-50"
            disabled={page <= 1}
            onClick={() => setPage((current) => current - 1)}
            type="button"
          >
            Trang trước
          </button>
          <span>
            Trang {page}/{Math.ceil(total / pageSize)}
          </span>
          <button
            className="min-h-10 rounded-lg border border-neutral-300 px-4 disabled:opacity-50"
            disabled={page * pageSize >= total}
            onClick={() => setPage((current) => current + 1)}
            type="button"
          >
            Trang sau
          </button>
        </nav>
      ) : null}
    </main>
  );
}
