"use client";

import { ExternalLink, Share2, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import type { Verification } from "@/lib/api/types";
import { displayCnsDossierCode } from "@/lib/brand/identifiers";

export function DigitalCertificate({ data }: { data: Verification }) {
  const [failedQr, setFailedQr] = useState<string | null>(null);
  if (!data.certificateNumber) return null;
  const verifyPath = `/verify/${encodeURIComponent(data.certificateNumber)}`;
  const workPath = data.publicWorkSlug
    ? `/works/${encodeURIComponent(data.publicWorkSlug)}`
    : null;
  const subject = data.recognizedSubject?.trim() || null;
  const valid = data.status === "VALID" && data.isCurrentVersion !== false;
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
    <article className="digital-certificate relative isolate overflow-hidden border-[3px] border-[#71121c] bg-[#fffdf5] p-1.5 text-[#261713] shadow-[0_28px_80px_rgba(16,8,5,.24)]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-55 [background-image:radial-gradient(circle_at_15%_8%,rgba(198,160,65,.18),transparent_28%),linear-gradient(rgba(126,19,27,.035)_1px,transparent_1px),linear-gradient(90deg,rgba(126,19,27,.035)_1px,transparent_1px)] [background-size:auto,24px_24px,24px_24px]"
      />
      <div className="h-2 bg-[#82141d] sm:h-3" />
      <Image
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute -right-20 top-24 -z-10 size-80 object-contain opacity-[0.13] sm:size-[32rem]"
        height={512}
        src="/assets/brand/trong-dong.png"
        width={512}
      />

      <div className="border border-[#b89543] p-4 sm:p-8 lg:p-12">
        <header className="flex flex-col items-center border-b-2 border-[#ad8231] pb-6 text-center sm:pb-8">
          <p className="text-xs font-semibold tracking-[0.16em] text-[#9b7427] uppercase sm:text-sm">
            Đề cử Tinh Hoa Việt
          </p>
          <h2 className="digital-certificate__heading mt-2 text-balance text-3xl font-bold uppercase text-[#2b1714] sm:text-5xl">
            Bằng xác lập
          </h2>
          <Image
            alt="Biểu trưng Tinh Hoa Việt"
            className="mt-3 size-24 shrink-0 scale-[1.2] [clip-path:circle(40%_at_center)] sm:size-32"
            height={256}
            src="/assets/brand/logo-tinh-hoa-viet.png"
            width={256}
          />
          <p className="mt-3 text-sm leading-6 text-[#503d32]">
            Ghi nhận tác phẩm · Tôn vinh giá trị Việt
          </p>
        </header>

        <div className="mt-5 px-1 sm:px-2">
          <p className="text-xs font-semibold tracking-[0.08em] text-[#9b7427] uppercase">
            Số bằng xác lập
          </p>
          <p className="mt-1 break-all font-mono text-base font-semibold text-[#82141d] sm:text-lg">
            {data.certificateNumber}
          </p>
          <p
            className={`mt-3 inline-flex items-center gap-2 text-sm font-bold ${valid ? "text-[#245b38]" : "text-[#76530c]"}`}
          >
            <ShieldCheck className="size-4" />
            {data.isCurrentVersion === false
              ? "Phiên bản cũ · đã có bản cập nhật"
              : statusLabel}
          </p>
        </div>

        <div className="grid gap-6 py-6 lg:grid-cols-[minmax(0,1fr)_11rem] lg:items-center lg:gap-12">
          <section className="min-w-0">
            <div className="digital-certificate__work-panel">
              <p className="text-xs font-semibold tracking-[0.08em] text-[#9b7427] uppercase sm:text-sm">
                Tác phẩm được ghi nhận
              </p>
              <h3 className="digital-certificate__work-title mt-5 text-pretty text-[#2b1714]">
                {data.assetTitle ?? "Tài sản số đã xác lập"}
              </h3>
              {data.assetSummary ? (
                <p className="mt-4 text-sm leading-6 text-[#503d32]">
                  {data.assetSummary}
                </p>
              ) : null}
            </div>
            <dl className="mt-5 grid gap-x-10 gap-y-4 text-sm sm:grid-cols-2">
              {subject ? (
                <CertificateFact
                  label="Người được ghi nhận trên bằng"
                  value={subject}
                />
              ) : null}
              {data.dossierCode ? (
                <CertificateFact
                  label="Mã hồ sơ đề cử"
                  mono
                  value={displayCnsDossierCode(data.dossierCode)}
                />
              ) : null}
              <CertificateFact label="Danh mục" value={data.categoryName} />
              <CertificateFact
                label="Đơn vị đề cử"
                value="Đề cử Tinh Hoa Việt"
              />
              <CertificateFact
                label="Phiên bản"
                value={data.version ? `Phiên bản ${data.version}` : null}
              />
              <CertificateFact
                label="Mạng ghi nhận"
                value={
                  data.network?.toLowerCase() === "polygon"
                    ? "Mạng blockchain Polygon"
                    : "Mạng blockchain"
                }
              />
            </dl>
          </section>

          <section className="mx-auto w-full max-w-44 text-center">
            <div className="border border-[#c9ad60] bg-white p-2 shadow-[0_8px_24px_rgba(65,42,20,.12)]">
              {failedQr !== data.certificateNumber ? (
                <Image
                  alt={`Mã QR kiểm tra bằng xác lập ${data.certificateNumber}`}
                  className="aspect-square size-full object-contain"
                  height={320}
                  loading="eager"
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
      <dt className="text-sm font-semibold text-[#765c27]">{label}</dt>
      <dd
        className={`mt-1 text-pretty leading-6 font-semibold text-[#2b1714] ${mono ? "break-all font-mono text-xs" : ""}`}
      >
        {value || "Chưa công bố"}
      </dd>
    </div>
  );
}
