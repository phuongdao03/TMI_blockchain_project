"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgeCheck,
  Download,
  ExternalLink,
  FileClock,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { useMemo, useState } from "react";

import { CertificatePdfViewer } from "@/components/certificates/certificate-pdf-viewer";
import { Feedback } from "@/components/ui/feedback";
import { certificateApi, dossierApi } from "@/lib/api/client";
import type {
  CertificateVersion,
  CertificateVersionStatus,
} from "@/lib/api/types";

const statusCopy: Record<
  CertificateVersionStatus,
  { label: string; description: string; tone: string }
> = {
  PENDING_APPROVAL: {
    label: "Đang chờ xem xét",
    description: "Yêu cầu đã được tiếp nhận và đang chờ kiểm tra.",
    tone: "bg-amber-50 text-amber-800",
  },
  REJECTED: {
    label: "Cần gửi lại",
    description: "Yêu cầu chưa được chấp thuận. Xem lý do để điều chỉnh.",
    tone: "bg-red-50 text-red-800",
  },
  ANCHOR_PENDING: {
    label: "Đang hoàn tất phát hành",
    description: "Thông tin đã được duyệt và đang hoàn tất bước xác nhận cuối.",
    tone: "bg-sky-50 text-sky-800",
  },
  FAILED: {
    label: "Tạm gián đoạn",
    description:
      "Hệ thống đang xử lý lại bước phát hành. Bản hiện tại vẫn có hiệu lực.",
    tone: "bg-orange-50 text-orange-800",
  },
  ACTIVE: {
    label: "Đang có hiệu lực",
    description: "Đây là phiên bản bằng xác lập đang được sử dụng.",
    tone: "bg-emerald-50 text-emerald-800",
  },
  SUPERSEDED: {
    label: "Đã được cập nhật",
    description: "Phiên bản này được giữ lại trong lịch sử đối chiếu.",
    tone: "bg-slate-100 text-slate-700",
  },
  REVOKED: {
    label: "Đã thu hồi",
    description: "Phiên bản này không còn hiệu lực.",
    tone: "bg-red-50 text-red-800",
  },
};

const openStatuses = new Set<CertificateVersionStatus>([
  "PENDING_APPROVAL",
  "ANCHOR_PENDING",
  "FAILED",
]);

function formatDate(value: string | null) {
  if (!value) return "Chưa cập nhật";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function VersionTimeline({
  certificateId,
  certificateNumber,
  versions,
}: {
  certificateId: string;
  certificateNumber: string;
  versions: CertificateVersion[];
}) {
  const [downloadError, setDownloadError] = useState<number | null>(null);

  async function downloadVersion(versionNo: number) {
    try {
      const blob = await certificateApi.downloadVersionPdf(
        certificateId,
        versionNo,
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${certificateNumber}-v${versionNo}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDownloadError(null);
    } catch {
      setDownloadError(versionNo);
    }
  }

  return (
    <ol className="mt-6 space-y-0">
      {versions.map((version, index) => {
        const copy = statusCopy[version.status];
        return (
          <li
            className="relative grid grid-cols-[2.5rem_1fr] gap-4"
            key={version.id}
          >
            {index < versions.length - 1 ? (
              <span className="absolute bottom-0 left-5 top-10 w-px bg-neutral-200" />
            ) : null}
            <span className="relative z-10 grid size-10 place-items-center rounded-full border border-neutral-200 bg-white text-sm font-bold text-primary-700">
              {version.versionNo}
            </span>
            <div className="pb-7">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-neutral-950">
                  Phiên bản {version.versionNo}
                </h3>
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-bold ${copy.tone}`}
                >
                  {copy.label}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-neutral-600">
                {copy.description}
              </p>
              {version.changeReason ? (
                <p className="mt-2 text-sm text-neutral-700">
                  <strong>Lý do cập nhật:</strong> {version.changeReason}
                </p>
              ) : null}
              {version.rejectionReason ? (
                <Feedback
                  className="mt-3"
                  title="Thông tin cần điều chỉnh"
                  tone="warning"
                >
                  {version.rejectionReason}
                </Feedback>
              ) : null}
              {version.pdfReady ? (
                <button
                  className="mt-2 text-sm font-bold text-primary-700 underline"
                  onClick={() => void downloadVersion(version.versionNo)}
                  type="button"
                >
                  Tải PDF phiên bản {version.versionNo}
                </button>
              ) : null}
              {downloadError === version.versionNo ? (
                <p className="mt-2 text-sm text-red-700" role="alert">
                  Không thể tải PDF phiên bản này.
                </p>
              ) : null}
              <p className="mt-2 text-xs text-neutral-400">
                {formatDate(version.requestedAt ?? version.createdAt)}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function CertificateDetail({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [downloadError, setDownloadError] = useState(false);
  const detail = useQuery({
    queryKey: ["certificate", id],
    queryFn: () => certificateApi.get(id),
  });
  const versions = useQuery({
    queryKey: ["certificate", id, "versions"],
    queryFn: () => certificateApi.versions(id),
  });
  const dossierVersions = useQuery({
    queryKey: ["dossier", detail.data?.certificate.dossierId, "versions"],
    queryFn: () => dossierApi.versions(detail.data!.certificate.dossierId),
    enabled: Boolean(detail.data?.certificate.dossierId),
  });
  const activeVersion = versions.data?.find((item) => item.status === "ACTIVE");
  const activeDossierVersion = dossierVersions.data?.find(
    (item) => item.id === activeVersion?.dossierVersionId,
  );
  const candidate = useMemo(
    () =>
      dossierVersions.data
        ?.filter(
          (item) => item.versionNo > (activeDossierVersion?.versionNo ?? 0),
        )
        .sort((left, right) => right.versionNo - left.versionNo)[0],
    [activeDossierVersion?.versionNo, dossierVersions.data],
  );
  const openRequest = versions.data?.find((item) =>
    openStatuses.has(item.status),
  );
  const requestVersion = useMutation({
    mutationFn: () =>
      certificateApi.requestVersion(id, {
        dossierVersionId: candidate!.id,
        reason: reason.trim(),
      }),
    onSuccess: async () => {
      setReason("");
      await queryClient.invalidateQueries({
        queryKey: ["certificate", id, "versions"],
      });
    },
  });

  if (detail.isPending || versions.isPending) {
    return (
      <div className="grid min-h-80 place-items-center" role="status">
        <LoaderCircle className="size-7 animate-spin text-primary-700" />
        <span className="sr-only">Đang tải bằng xác lập</span>
      </div>
    );
  }
  if (detail.error || versions.error || !detail.data || !versions.data) {
    return (
      <Feedback title="Không thể tải bằng xác lập" tone="error">
        Vui lòng thử lại sau.
      </Feedback>
    );
  }
  const certificate = detail.data.certificate;
  const networkLabel =
    certificate.network?.toLowerCase() === "polygon"
      ? "Mạng blockchain Polygon"
      : "Mạng blockchain";

  async function downloadPdf() {
    try {
      const blob = await certificateApi.downloadPdf(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${certificate.certificateNumber}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setDownloadError(true);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-4 sm:space-y-6">
      <Link
        className="inline-flex items-center gap-2 text-sm font-bold text-neutral-600 hover:text-primary-700"
        href="/certificates"
      >
        <ArrowLeft className="size-4" /> Quay lại danh sách
      </Link>

      <section className="relative overflow-hidden rounded-[1.25rem] bg-neutral-950 p-5 text-white shadow-xl sm:rounded-[2rem] sm:p-10 sm:shadow-2xl">
        <div className="absolute -right-20 -top-20 size-72 rounded-full bg-primary-600/20 blur-3xl" />
        <div className="relative grid gap-4 sm:gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.1em] text-amber-300 sm:tracking-[0.2em]">
              <BadgeCheck className="size-4" /> Bằng xác lập tài sản số
            </p>
            <h1 className="mt-3 max-w-3xl text-2xl font-bold leading-tight tracking-tight sm:mt-4 sm:text-4xl">
              {certificate.assetTitle}
            </h1>
            <p className="mt-2 break-all font-mono text-sm text-slate-300 sm:mt-4">
              {certificate.certificateNumber}
            </p>
            <button
              className="mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#f6c515] px-5 text-sm font-bold text-[#3b1114] disabled:cursor-not-allowed disabled:opacity-50 sm:mt-6 sm:min-h-12 sm:w-auto"
              disabled={!certificate.pdfReady}
              onClick={() => void downloadPdf()}
              type="button"
            >
              <Download aria-hidden="true" className="size-5" />
              {certificate.pdfReady
                ? "Tải bằng xác lập PDF"
                : "PDF đang chuẩn bị"}
            </button>
            {downloadError ? (
              <p className="mt-3 text-sm text-red-200" role="alert">
                Không thể tải PDF. Vui lòng thử lại.
              </p>
            ) : null}
          </div>
          <div
            className={`rounded-xl border px-4 py-3 sm:rounded-2xl sm:px-5 sm:py-4 ${certificate.status === "ACTIVE" ? "border-emerald-400/20 bg-emerald-400/10" : "border-amber-300/25 bg-amber-300/10"}`}
          >
            <p
              className={`flex items-center gap-2 font-bold ${certificate.status === "ACTIVE" ? "text-emerald-300" : "text-amber-200"}`}
            >
              <ShieldCheck className="size-5" />
              {certificate.status === "ACTIVE"
                ? "Đang có hiệu lực"
                : certificate.status === "REVOKED"
                  ? "Đã thu hồi"
                  : "Đã hết hiệu lực"}
            </p>
            <p className="mt-1 text-xs text-emerald-100/70">
              Phiên bản {certificate.currentVersionNo}
            </p>
          </div>
        </div>
      </section>

      {certificate.pdfReady ? (
        <CertificatePdfViewer
          certificateId={id}
          certificateNumber={certificate.certificateNumber}
          onDownload={() => void downloadPdf()}
        />
      ) : (
        <div className="grid min-h-48 place-items-center rounded-xl border border-dashed border-neutral-300 bg-white text-sm text-neutral-600">
          Bản PDF đang được chuẩn bị.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-3xl border border-neutral-200 bg-white p-6 sm:p-8">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            Tiến trình cập nhật
          </p>
          <h2 className="mt-2 text-2xl font-bold">Lịch sử bằng xác lập</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
            Mỗi lần điều chỉnh được lưu thành một phiên bản mới. Bản cũ không bị
            xóa và vẫn có thể đối chiếu khi cần.
          </p>
          <VersionTimeline
            certificateId={id}
            certificateNumber={certificate.certificateNumber}
            versions={versions.data}
          />
        </section>

        <div className="space-y-6">
          <section
            id="certificate-update"
            className="scroll-mt-24 rounded-3xl border border-neutral-200 bg-white p-6"
          >
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <RefreshCw className="size-5 text-primary-700" /> Cập nhật bằng
              xác lập
            </h2>
            {openRequest ? (
              <Feedback
                className="mt-4"
                title={statusCopy[openRequest.status].label}
                tone="info"
              >
                {statusCopy[openRequest.status].description}
              </Feedback>
            ) : candidate ? (
              <form
                className="mt-4 space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  requestVersion.mutate();
                }}
              >
                <p className="text-sm leading-6 text-neutral-600">
                  Hồ sơ có thông tin mới đã được xét duyệt. Hãy nêu rõ lý do để
                  gửi yêu cầu cập nhật bằng xác lập.
                </p>
                <label
                  className="block text-sm font-bold"
                  htmlFor="change-reason"
                >
                  Lý do cập nhật
                </label>
                <textarea
                  className="min-h-32 w-full rounded-xl border border-neutral-300 px-4 py-3 text-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
                  id="change-reason"
                  maxLength={2000}
                  minLength={20}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Ví dụ: Cập nhật thông tin chủ thể theo tài liệu đã được phê duyệt…"
                  required
                  value={reason}
                />
                {requestVersion.error ? (
                  <Feedback title="Chưa thể gửi yêu cầu" tone="error">
                    Kiểm tra lại nội dung hoặc thử lại sau.
                  </Feedback>
                ) : null}
                <button
                  className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary-600 px-4 text-sm font-bold text-white disabled:opacity-50"
                  disabled={
                    reason.trim().length < 20 || requestVersion.isPending
                  }
                  type="submit"
                >
                  {requestVersion.isPending ? (
                    <LoaderCircle className="size-4 animate-spin" />
                  ) : (
                    <FileClock className="size-4" />
                  )}
                  Gửi yêu cầu cập nhật
                </button>
              </form>
            ) : (
              <div className="mt-4">
                <Feedback title="Chưa có thay đổi cần cập nhật" tone="success">
                  Khi hồ sơ có phiên bản mới được phê duyệt, bạn có thể gửi yêu
                  cầu tại đây.
                </Feedback>
                <Link
                  className="mt-4 inline-flex min-h-11 items-center font-bold text-primary-700"
                  href={`/dossiers/${certificate.dossierId}`}
                >
                  Xem hồ sơ liên quan →
                </Link>
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-neutral-200 bg-white p-6">
            <div className="grid gap-5 sm:grid-cols-[8rem_1fr] sm:items-center">
              <div className="rounded-2xl border border-neutral-200 bg-white p-2 shadow-sm">
                <Image
                  alt="Mã QR kiểm tra bằng xác lập"
                  className="aspect-square size-full"
                  height={240}
                  src={`/api/v1/certificates/${encodeURIComponent(id)}/qr`}
                  unoptimized
                  width={240}
                />
              </div>
              <div>
                <h2 className="font-bold">Tra cứu bằng xác lập</h2>
                <p className="mt-2 text-sm leading-6 text-neutral-600">
                  Xem thông tin ghi nhận và tình trạng hiện tại của bằng xác
                  lập.
                </p>
                <p className="mt-2 break-all font-mono text-xs text-neutral-500">
                  {detail.data.qrPayload}
                </p>
              </div>
            </div>
            <a
              className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-neutral-950 text-sm font-bold text-white"
              href={`/verify/${encodeURIComponent(certificate.certificateNumber)}`}
            >
              Mở trang tra cứu <ExternalLink className="size-4" />
            </a>
          </section>
        </div>
      </div>

      <details className="rounded-2xl border border-neutral-200 bg-white px-5 py-4">
        <summary className="cursor-pointer font-bold text-neutral-800">
          Xem thông tin đối chiếu nâng cao
        </summary>
        <dl className="mt-5 grid gap-4 text-sm md:grid-cols-2">
          {[
            [
              "Mạng xác nhận",
              certificate.network ? networkLabel : "Đang cập nhật",
            ],
            ["Mã giao dịch", certificate.transactionHash ?? "Chưa có"],
            ["Mã toàn vẹn", detail.data.metadataHash],
            ["Số lượt xác nhận", String(certificate.confirmations)],
          ].map(([label, value]) => (
            <div className="rounded-xl bg-neutral-50 p-4" key={label}>
              <dt className="text-xs font-bold uppercase tracking-wider text-neutral-500">
                {label}
              </dt>
              <dd className="mt-2 break-all font-mono text-neutral-800">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  );
}
