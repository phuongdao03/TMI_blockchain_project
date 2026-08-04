"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, ExternalLink, LoaderCircle, ShieldCheck } from "lucide-react";

import { certificateApi } from "@/lib/api/client";

export function CertificateDetail({ id }: { id: string }) {
  const query = useQuery({
    queryKey: ["certificate", id],
    queryFn: () => certificateApi.get(id),
  });
  const download = useMutation({
    mutationFn: () => certificateApi.download(id),
    onSuccess: ({ url }) => window.open(url, "_blank", "noopener,noreferrer"),
  });
  if (query.isPending) {
    return <LoaderCircle className="mx-auto mt-24 size-7 animate-spin" />;
  }
  if (query.error || !query.data) {
    return <div role="alert">Không thể tải chứng thư.</div>;
  }
  const certificate = query.data.certificate;
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section className="relative overflow-hidden rounded-[2rem] bg-ink-950 p-7 text-white shadow-2xl sm:p-10">
        <div className="absolute -right-20 -top-20 size-72 rounded-full bg-primary-600/20 blur-3xl" />
        <div className="relative flex flex-col justify-between gap-8 lg:flex-row">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
              Chứng thư tài sản số
            </p>
            <h1 className="mt-4 max-w-3xl text-3xl font-bold tracking-tight sm:text-5xl">
              {certificate.assetTitle}
            </h1>
            <p className="mt-4 font-mono text-sm text-slate-300">
              {certificate.certificateNumber}
            </p>
          </div>
          <span className="inline-flex h-fit items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-sm font-bold text-emerald-300">
            <ShieldCheck className="size-4" /> {certificate.status}
          </span>
        </div>
      </section>
      <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
        <section className="rounded-3xl border bg-white p-6 sm:p-8">
          <h2 className="text-xl font-bold">Bằng chứng blockchain</h2>
          <dl className="mt-6 grid gap-5 text-sm">
            {[
              ["Mạng", certificate.network ?? "Đang cập nhật"],
              ["Địa chỉ hợp đồng", certificate.contractAddress ?? "—"],
              ["Giao dịch", certificate.transactionHash ?? "—"],
              ["Metadata hash", query.data.metadataHash],
              ["Số xác nhận", String(certificate.confirmations)],
            ].map(([label, value]) => (
              <div className="border-b pb-4" key={label}>
                <dt className="text-xs font-bold uppercase tracking-wider text-neutral-400">{label}</dt>
                <dd className="mt-2 break-all font-mono text-neutral-800">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
        <aside className="rounded-3xl border bg-white p-6">
          <h2 className="font-bold">Tệp chứng thư</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-500">
            Liên kết tải được ký riêng và chỉ có hiệu lực trong thời gian ngắn.
          </p>
          <button
            className="mt-5 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary-600 px-4 text-sm font-bold text-white disabled:opacity-50"
            disabled={!certificate.pdfReady || download.isPending}
            onClick={() => download.mutate()}
            type="button"
          >
            {download.isPending ? <LoaderCircle className="size-4 animate-spin" /> : <Download className="size-4" />}
            Tải PDF bảo mật
          </button>
          <a
            className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border text-sm font-bold"
            href={query.data.qrPayload}
            rel="noreferrer"
            target="_blank"
          >
            Xác minh công khai <ExternalLink className="size-4" />
          </a>
        </aside>
      </div>
    </div>
  );
}
