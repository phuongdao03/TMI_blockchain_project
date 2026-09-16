"use client";

import { ExternalLink, Share2, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import type { Verification } from "@/lib/api/types";

function date(value: string | null): string {
  if (!value) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export function DigitalCertificate({ data }: { data: Verification }) {
  const [failedQr, setFailedQr] = useState<string | null>(null);
  if (!data.certificateNumber) return null;
  const verifyPath = `/verify/${encodeURIComponent(data.certificateNumber)}`;
  const workPath = data.publicWorkSlug
    ? `/works/${encodeURIComponent(data.publicWorkSlug)}`
    : null;
  const valid = data.status === "VALID";

  async function share() {
    const url = new URL(verifyPath, window.location.origin).toString();
    if (navigator.share) {
      await navigator.share({
        title: `Chứng thư ${data.certificateNumber}`,
        text: data.assetTitle ?? "Chứng thư xác lập tài sản số",
        url,
      });
      return;
    }
    await navigator.clipboard.writeText(url);
  }

  return (
    <article className="digital-certificate relative isolate overflow-hidden border border-[#d6b968] bg-[#fffdf5] text-[#261713] shadow-[0_28px_80px_rgba(16,8,5,.24)]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-55 [background-image:radial-gradient(circle_at_15%_8%,rgba(198,160,65,.18),transparent_28%),linear-gradient(rgba(126,19,27,.035)_1px,transparent_1px),linear-gradient(90deg,rgba(126,19,27,.035)_1px,transparent_1px)] [background-size:auto,24px_24px,24px_24px]"
      />
      <div className="h-2 bg-[#82141d] sm:h-3" />

      <div className="p-5 sm:p-8 lg:p-12">
        <header className="digital-certificate__header grid gap-5 border-b border-[#d8c798] pb-6 sm:grid-cols-[auto_1fr] sm:items-center lg:grid-cols-[8rem_1fr_auto]">
          <p className="digital-certificate__organization">
            Trung tâm An ninh Công nghệ số – CNS
          </p>
          <Image
            alt="Logo Tinh Hoa Việt trên chứng thư"
            className="mx-auto size-24 object-contain drop-shadow-[0_8px_14px_rgba(100,18,18,.2)] sm:mx-0 lg:size-28"
            height={224}
            priority
            src="/assets/brand/thv-certificate-seal.png"
            width={224}
          />
          <div className="text-center sm:text-left">
            <h2 className="mt-2 text-balance font-serif text-3xl leading-none font-black tracking-[-0.035em] text-[#2b1714] sm:text-4xl lg:text-5xl">
              Chứng thư xác lập tài sản số
            </h2>
          </div>
          <div className="border-t border-[#d8c798] pt-4 text-center sm:col-span-2 sm:text-left lg:col-span-1 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-6 lg:text-right">
            <p className="text-[0.65rem] font-bold tracking-[0.18em] text-[#6d5949] uppercase">
              Số chứng thư
            </p>
            <p className="mt-1 break-all font-mono text-sm font-black text-[#82141d] sm:text-base">
              {data.certificateNumber}
            </p>
          </div>
        </header>

        <div className="grid gap-8 py-8 lg:grid-cols-[minmax(0,1fr)_11rem] lg:items-center lg:gap-12">
          <section>
            <p className="text-[0.68rem] font-black tracking-[0.18em] text-[#765c27] uppercase">
              Tác phẩm được ghi nhận
            </p>
            <h3 className="mt-3 text-pretty font-serif text-3xl leading-tight font-black text-[#2b1714] sm:text-4xl">
              {data.assetTitle ?? "Tài sản số đã xác lập"}
            </h3>
            <dl className="mt-7 grid gap-x-10 gap-y-5 text-sm sm:grid-cols-2">
              <CertificateFact
                label="Tác giả/người được ghi nhận"
                value={data.recognizedSubject}
              />
              <CertificateFact
                label="Mã tác phẩm"
                mono
                value={data.dossierCode}
              />
              <CertificateFact
                label="Đơn vị xác lập"
                value={data.issuerLabel}
              />
              <CertificateFact
                label="Ngày ghi nhận"
                value={date(data.confirmedAt ?? data.issuedAt)}
              />
              <CertificateFact
                label="Phiên bản"
                value={data.version ? `Phiên bản ${data.version}` : null}
              />
              <CertificateFact
                label="Mạng ghi nhận"
                value={
                  data.network === "polygon" ? "Polygon Mainnet" : data.network
                }
              />
            </dl>
          </section>

          <section className="mx-auto w-full max-w-44 text-center">
            <div className="border border-[#c9ad60] bg-white p-2 shadow-[0_8px_24px_rgba(65,42,20,.12)]">
              {failedQr !== data.certificateNumber ? (
                <Image
                  alt={`Mã QR kiểm tra chứng thư ${data.certificateNumber}`}
                  className="aspect-square size-full object-contain"
                  height={320}
                  src={`/api/v1/verify/certificate/${encodeURIComponent(data.certificateNumber)}/qr`}
                  onError={() => setFailedQr(data.certificateNumber)}
                  unoptimized
                  width={320}
                />
              ) : (
                <a
                  className="flex aspect-square items-center justify-center p-3 text-sm font-bold text-[#82141d]"
                  href={verifyPath}
                >
                  Mở trang kiểm tra chứng thư
                </a>
              )}
            </div>
            <p className="mt-3 text-xs leading-5 font-bold text-[#503d32]">
              Quét mã để mở trang kiểm tra công khai
            </p>
          </section>
        </div>

        <footer className="grid gap-6 border-t border-[#d8c798] pt-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div className="min-w-0">
            <p className="text-[0.65rem] font-black tracking-[0.16em] text-[#765c27] uppercase">
              Dấu vân tay số SHA-256
            </p>
            <p className="mt-2 break-all font-mono text-[0.68rem] leading-5 text-[#503d32] sm:text-xs">
              {data.metadataHash ?? "Đang cập nhật"}
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3 lg:flex lg:flex-wrap lg:justify-end">
            <span
              className={`inline-flex min-h-11 items-center justify-center gap-2 border px-4 text-center text-sm font-black ${valid ? "border-[#9bc8aa] bg-[#edf8f0] text-[#245b38]" : "border-[#d8b66a] bg-[#fff7df] text-[#76530c]"}`}
            >
              <ShieldCheck className="size-4" />
              {valid ? "Đang có hiệu lực" : "Đang đối chiếu"}
            </span>
            <button
              className="inline-flex min-h-11 items-center justify-center gap-2 border border-[#b78e4b] bg-transparent px-4 text-sm font-bold text-[#82141d] transition hover:bg-[#f7ecd0] active:translate-y-px"
              onClick={() => void share()}
              type="button"
            >
              <Share2 className="size-4" /> Chia sẻ
            </button>
            {workPath ? (
              <a className="digital-certificate__verify" href={workPath}>
                Xem tác phẩm <ExternalLink className="size-4" />
              </a>
            ) : data.explorerUrl ? (
              <a
                className="digital-certificate__verify"
                href={data.explorerUrl}
                rel="noopener noreferrer"
                target="_blank"
              >
                Kiểm tra trên blockchain <ExternalLink className="size-4" />
              </a>
            ) : null}
          </div>
        </footer>
      </div>
    </article>
  );
}

function CertificateFact({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
}) {
  return (
    <div className="border-l-2 border-[#e1d5b5] pl-3">
      <dt className="text-xs font-bold text-[#765c27]">{label}</dt>
      <dd
        className={`mt-1 leading-6 font-semibold text-[#2b1714] ${mono ? "break-all font-mono text-xs" : ""}`}
      >
        {value || "Chưa công bố"}
      </dd>
    </div>
  );
}
