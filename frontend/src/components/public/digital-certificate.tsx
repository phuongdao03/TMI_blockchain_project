"use client";

import { ExternalLink, Share2, ShieldCheck } from "lucide-react";
import Image from "next/image";

import type { Verification } from "@/lib/api/types";

function date(value: string | null): string {
  if (!value) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export function DigitalCertificate({ data }: { data: Verification }) {
  if (!data.certificateNumber) return null;
  const verifyPath = `/verify/${encodeURIComponent(data.certificateNumber)}`;
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
    <article className="digital-certificate relative overflow-hidden rounded-xl border-2 border-[#6f1117] bg-[#f4ecd2] p-1 text-[#281a16] shadow-[0_16px_48px_rgba(0,0,0,.24)] sm:rounded-[2rem] sm:border-[6px] sm:p-5">
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 size-full opacity-25"
        preserveAspectRatio="none"
        viewBox="0 0 1200 760"
      >
        <defs>
          <pattern
            height="18"
            id="security-wave"
            patternUnits="userSpaceOnUse"
            width="18"
          >
            <path
              d="M0 9 Q4 0 9 9 T18 9"
              fill="none"
              stroke="#8d6b22"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect fill="url(#security-wave)" height="100%" width="100%" />
        <rect
          fill="none"
          height="710"
          rx="20"
          stroke="#8b1118"
          strokeWidth="3"
          width="1150"
          x="25"
          y="25"
        />
      </svg>

      <div className="relative rounded-lg border border-[#9b7a35] bg-[#f8f1da]/95 p-4 sm:rounded-2xl sm:p-8 lg:p-10">
        <header className="flex flex-col gap-5 border-b-2 border-[#9b7a35] pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-black tracking-[0.22em] text-[#8b1118] uppercase">
              Tổ chức Đề cử và xác lập Tinh Hoa Việt
            </p>
            <h2 className="mt-3 font-serif text-2xl font-black tracking-tight sm:text-5xl">
              Chứng thư xác lập tài sản số
            </h2>
          </div>
          <div className="shrink-0 text-left sm:text-right">
            <p className="text-xs font-bold tracking-[0.18em] uppercase">
              Số chứng thư
            </p>
            <p className="mt-1 break-all font-mono text-sm font-black text-[#8b1118] sm:text-lg">
              {data.certificateNumber}
            </p>
          </div>
        </header>

        <div className="grid gap-7 py-8 lg:grid-cols-[1fr_12rem] lg:items-center">
          <div>
            <p className="text-xs font-bold tracking-[0.18em] text-[#74551f] uppercase">
              Tác phẩm được ghi nhận
            </p>
            <h3 className="mt-2 break-words font-serif text-2xl font-black sm:text-4xl">
              {data.assetTitle ?? "Tài sản số đã xác lập"}
            </h3>
            <dl className="mt-7 grid gap-x-8 gap-y-5 text-sm sm:grid-cols-2">
              <CertificateFact
                label="Tác giả/người được ghi nhận"
                value={data.recognizedSubject}
              />
              <CertificateFact label="Chủ thể hồ sơ" value={data.dossierCode} />
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
          </div>

          <div className="mx-auto w-full max-w-48">
            <div className="rounded-xl border-2 border-[#9b7a35] bg-white p-2">
              <Image
                alt={`Mã QR kiểm tra chứng thư ${data.certificateNumber}`}
                className="aspect-square size-full"
                height={320}
                src={`/api/v1/public/verify/certificate/${encodeURIComponent(data.certificateNumber)}/qr`}
                unoptimized
                width={320}
              />
            </div>
            <p className="mt-2 text-center text-[11px] font-bold">
              Quét để kiểm tra công khai
            </p>
          </div>
        </div>

        <div className="grid gap-5 border-t-2 border-[#9b7a35] pt-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="text-xs font-bold tracking-[0.16em] text-[#74551f] uppercase">
              Dấu vân tay số SHA-256
            </p>
            <p className="mt-2 break-all font-mono text-xs leading-5">
              {data.metadataHash ?? "Đang cập nhật"}
            </p>
          </div>
          <div className="grid gap-3 sm:flex sm:flex-wrap sm:items-center">
            <span
              className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-full border px-4 text-center text-sm font-black ${valid ? "border-emerald-700 bg-emerald-50 text-emerald-800" : "border-amber-700 bg-amber-50 text-amber-900"}`}
            >
              <ShieldCheck className="size-4" />
              {valid ? "Đang có hiệu lực" : "Đang đối chiếu"}
            </span>
            <button
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-[#8b1118] px-4 text-sm font-bold text-[#8b1118]"
              onClick={() => void share()}
              type="button"
            >
              <Share2 className="size-4" /> Chia sẻ
            </button>
            <a
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-[#8b1118] px-4 text-sm font-bold text-white"
              href={verifyPath}
            >
              Kiểm tra <ExternalLink className="size-4" />
            </a>
          </div>
        </div>
      </div>
    </article>
  );
}

function CertificateFact({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div>
      <dt className="text-xs font-bold text-[#74551f]">{label}</dt>
      <dd className="mt-1 font-semibold">{value || "Chưa công bố"}</dd>
    </div>
  );
}
