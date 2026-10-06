"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, LoaderCircle, Search } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { adminCertificateApi } from "@/lib/api/client";

const pageSize = 10;

export function CertificateCorrectionList() {
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["admin", "certificate-corrections", search, page],
    queryFn: () =>
      adminCertificateApi.list({
        page,
        pageSize,
        search: search || undefined,
        status: "ACTIVE",
      }),
  });

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
    setPage(1);
  }

  return (
    <div className="space-y-5">
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={submitSearch}
        role="search"
      >
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">Tìm bằng đã cấp</span>
          <Search
            aria-hidden="true"
            className="absolute left-3 top-3.5 size-4 text-neutral-500"
          />
          <input
            className="min-h-11 w-full rounded-xl border border-neutral-300 bg-white pl-10 pr-3 text-sm"
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Số bằng, mã hồ sơ hoặc tên tác phẩm"
            type="search"
            value={searchDraft}
          />
        </label>
        <button
          className="min-h-11 rounded-xl bg-primary-700 px-5 text-sm font-bold text-white"
          type="submit"
        >
          Tìm kiếm
        </button>
      </form>

      {query.isPending ? (
        <p
          className="flex items-center gap-2 text-sm text-neutral-600"
          role="status"
        >
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />{" "}
          Đang tải bằng đã cấp…
        </p>
      ) : null}
      {query.isError ? (
        <p className="text-sm text-red-700" role="alert">
          Không thể tải danh sách bằng.{" "}
          <button
            className="font-bold underline"
            onClick={() => void query.refetch()}
            type="button"
          >
            Thử lại
          </button>
        </p>
      ) : null}
      {query.data?.data.length === 0 ? (
        <p className="rounded-xl border border-dashed border-neutral-300 bg-white p-6 text-sm text-neutral-600">
          Không tìm thấy bằng đang có hiệu lực. Hãy thử số bằng hoặc mã hồ sơ
          khác.
        </p>
      ) : null}
      {query.data && query.data.data.length > 0 ? (
        <section
          aria-label="Bằng đã cấp"
          className="divide-y divide-neutral-200 overflow-hidden rounded-xl border border-neutral-200 bg-white"
        >
          {query.data.data.map(({ certificate }) => {
            const isThv = certificate.certificateNumber.startsWith("THV-");
            const canCorrect =
              isThv &&
              certificate.blockchainStatus === "CONFIRMED" &&
              Boolean(certificate.transactionHash);
            return (
              <article
                className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
                key={certificate.id}
              >
                <div className="min-w-0">
                  <p className="font-mono text-sm font-bold text-primary-700">
                    {certificate.certificateNumber}
                  </p>
                  <h2 className="mt-1 break-words font-bold text-neutral-950">
                    {certificate.assetTitle}
                  </h2>
                  <p className="mt-1 text-xs text-neutral-600">
                    Hồ sơ {certificate.dossierCode} · Phiên bản{" "}
                    {certificate.currentVersionNo}
                  </p>
                  {!isThv ? (
                    <p className="mt-1 text-xs text-amber-800">
                      Bằng định dạng cũ cần chuyển sang định dạng THV trước khi
                      sửa nội dung.
                    </p>
                  ) : null}
                  {isThv && !canCorrect ? (
                    <p className="mt-1 text-xs text-amber-800">
                      Bằng THV cần có bản ghi blockchain đã xác nhận trước khi
                      sửa nội dung.
                    </p>
                  ) : null}
                </div>
                {canCorrect ? (
                  <Link
                    aria-label={`Sửa nội dung ${certificate.certificateNumber}`}
                    className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg border border-primary-700 px-4 text-sm font-bold text-primary-700 hover:bg-primary-50"
                    href={`/admin/certificates/corrections/${encodeURIComponent(certificate.id)}`}
                  >
                    Sửa nội dung{" "}
                    <ArrowRight aria-hidden="true" className="size-4" />
                  </Link>
                ) : null}
              </article>
            );
          })}
        </section>
      ) : null}
      {query.data && query.data.meta.total > pageSize ? (
        <nav
          aria-label="Trang bằng đã cấp"
          className="flex items-center justify-between gap-3 text-sm font-semibold"
        >
          <button
            className="min-h-10 rounded-lg border border-neutral-300 px-4 disabled:opacity-50"
            disabled={page <= 1}
            onClick={() => setPage((value) => value - 1)}
            type="button"
          >
            Trang trước
          </button>
          <span>
            Trang {page}/{Math.ceil(query.data.meta.total / pageSize)}
          </span>
          <button
            className="min-h-10 rounded-lg border border-neutral-300 px-4 disabled:opacity-50"
            disabled={page * pageSize >= query.data.meta.total}
            onClick={() => setPage((value) => value + 1)}
            type="button"
          >
            Trang sau
          </button>
        </nav>
      ) : null}
    </div>
  );
}
