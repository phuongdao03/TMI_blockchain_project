"use client";

import { ExternalLink, Share2, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import type { Verification } from "@/lib/api/types";
import { displayCnsDossierCode } from "@/lib/brand/identifiers";

function date(value: string | null): string {
  if (!value) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

function recognizedSubject(value: string | null | undefined): string | null {
  return value === "Chủ thể hồ sơ CNS" ||
    value === "Chủ thể hồ sơ TMI" ||
    value === "Chưa công bố"
    ? null
    : (value ?? null);
}

export function DigitalCertificate({ data }: { data: Verification }) {
  const [failedQr, setFailedQr] = useState<string | null>(null);
  if (!data.certificateNumber) return null;
  const verifyPath = `/verify/${encodeURIComponent(data.certificateNumber)}`;
  const workPath = data.publicWorkSlug
    ? `/works/${encodeURIComponent(data.publicWorkSlug)}`
    : null;
  const valid = data.status === "VALID";
  const statusLabel = {
    VALID: "Đang có hiệu lực",
    REVOKED: "Đã thu hồi",
    EXPIRED: "Đã hết hạn",
    MISMATCH: "Thông tin chưa khớp",
    PENDING: "Đang đối chiếu",
    NOT_FOUND: "Không tìm thấy",
  }[data.status];

  async function share() {
    const url = new URL(verifyPath, window.location.origin).toString();
    if (navigator.share) {
      await navigator.share({
        title: `Bằng xác lập ${data.certificateNumber}`,
        text: data.assetTitle ?? "Bằng xác lập Tinh Hoa Việt",
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
      <Image
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute -right-20 top-28 -z-10 size-80 object-contain opacity-[0.07] sm:size-[32rem]"
        height={512}
        src="/assets/brand/trong-dong.png"
        width={512}
      />

      <div className="p-5 sm:p-8 lg:p-12">
        <header className="flex flex-col items-center gap-5 border-b border-[#d8c798] pb-7 text-center sm:flex-row sm:text-left">
          <Image
            alt="Biểu trưng Tinh Hoa Việt"
            className="size-28 shrink-0 object-contain drop-shadow-[0_8px_14px_rgba(100,18,18,.2)] sm:size-32"
            height={256}
            priority
            src="/assets/brand/logo-tinh-hoa-viet.png"
            width={256}
          />
          <div className="min-w-0 flex-1">
            <p className="text-[0.65rem] font-black tracking-[0.22em] text-[#765c27] uppercase">
              Đề cử Tinh Hoa Việt · Ghi nhận giá trị Việt
            </p>
            <h2 className="mt-2 text-balance font-serif text-3xl leading-tight font-black tracking-[-0.035em] text-[#2b1714] sm:text-4xl lg:text-5xl">
              Bằng xác lập
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#503d32]">
              Thông tin ghi nhận và đường dẫn kiểm tra công khai
            </p>
          </div>
        </header>

        <div className="mt-6 border-l-4 border-[#ad8231] bg-[#f6efdc] px-4 py-3">
          <p className="text-[0.65rem] font-black tracking-[0.16em] text-[#765c27] uppercase">
            Số bằng xác lập
          </p>
          <p className="mt-1 break-all font-mono text-base font-black text-[#82141d]">
            {data.certificateNumber}
          </p>
        </div>

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
                label={
                  recognizedSubject(data.recognizedSubject)
                    ? "Người được ghi nhận trên bằng"
                    : "Tác giả công khai của tác phẩm"
                }
                value={
                  recognizedSubject(data.recognizedSubject) ??
                  data.publicAuthorDisplayName
                }
              />
              <CertificateFact
                label="Mã tác phẩm"
                mono
                value={displayCnsDossierCode(data.dossierCode)}
              />
              <CertificateFact
                label="Đơn vị đề cử"
                value="Đề cử Tinh Hoa Việt"
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
            {!recognizedSubject(data.recognizedSubject) &&
            data.publicAuthorDisplayName ? (
              <p className="mt-5 border-l-2 border-[#ad8231] pl-3 text-xs leading-5 text-[#6d5949]">
                Tên tác giả lấy từ trang tác phẩm công khai. Bản ghi bằng đã
                phát hành không được thay đổi.
              </p>
            ) : null}
          </section>

          <section className="mx-auto w-full max-w-44 text-center">
            <div className="border border-[#c9ad60] bg-white p-2 shadow-[0_8px_24px_rgba(65,42,20,.12)]">
              {failedQr !== data.certificateNumber ? (
                <Image
                  alt={`Mã QR kiểm tra bằng xác lập ${data.certificateNumber}`}
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
                  Mở trang kiểm tra bằng xác lập
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
              {statusLabel}
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
        className={`mt-1 text-pretty leading-6 font-semibold text-[#2b1714] ${mono ? "break-all font-mono text-xs" : ""}`}
      >
        {value || "Chưa công bố"}
      </dd>
    </div>
  );
}
