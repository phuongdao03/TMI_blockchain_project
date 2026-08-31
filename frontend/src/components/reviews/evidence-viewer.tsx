"use client";

import { useMutation } from "@tanstack/react-query";
import {
  Download,
  ExternalLink,
  FileAudio,
  FileImage,
  FileText,
  FileVideo,
  LoaderCircle,
  ShieldCheck,
  X,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PrivateDocumentVerification } from "@/components/documents/private-document-verification";
import { mediaApi } from "@/lib/api/client";
import type { ReviewEvidenceSnapshot } from "@/lib/api/types";

function formatBytes(bytes: number) {
  const divisor = bytes >= 1_048_576 ? 1_048_576 : 1_024;
  return `${new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 1,
  }).format(bytes / divisor)} ${divisor === 1_048_576 ? "MB" : "KB"}`;
}

export function EvidenceViewer({
  evidences,
}: {
  evidences: ReviewEvidenceSnapshot[];
}) {
  const [activeMediaId, setActiveMediaId] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    evidence: ReviewEvidenceSnapshot;
    url: string;
  } | null>(null);
  const mutation = useMutation({
    mutationFn: mediaApi.signedUrl,
    onSuccess: (delivery, mediaId) => {
      const evidence = evidences.find(
        (item) => item.mediaAssetId === mediaId,
      );
      if (evidence) setPreview({ evidence, url: delivery.url });
    },
  });

  return (
    <Card className="overflow-hidden">
      <div className="border-b px-6 py-5 sm:px-8">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
          <ShieldCheck aria-hidden="true" className="size-4" />
          Bằng chứng phiên bản đã khóa
        </p>
        <h2 className="mt-2 text-xl font-bold">
          Tài liệu kiểm chứng ({evidences.length})
        </h2>
      </div>
      {evidences.length ? (
        <div className="divide-y">
          {evidences.map((evidence) => {
            const Icon = evidence.media.mimeType.startsWith("image/")
              ? FileImage
              : evidence.media.mimeType.startsWith("audio/")
                ? FileAudio
                : evidence.media.mimeType.startsWith("video/")
                  ? FileVideo
                  : FileText;
            const opening =
              mutation.isPending && activeMediaId === evidence.mediaAssetId;
            return (
              <article
                className="grid grid-cols-[auto_minmax(0,1fr)] gap-4 p-5 sm:items-center sm:px-8"
                key={evidence.id}
              >
                <span className="grid size-11 place-items-center rounded-xl bg-primary-50 text-primary-700">
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <div className="min-w-0">
                  <h3 className="font-bold text-neutral-950">
                    {evidence.title}
                  </h3>
                  <p className="mt-1 text-xs text-neutral-500">
                    {evidence.evidenceType} ·{" "}
                    {formatBytes(evidence.media.bytes)} ·{" "}
                    {evidence.media.mimeType}
                  </p>
                  {evidence.description ? (
                    <p className="mt-2 text-sm leading-6 text-neutral-600">
                      {evidence.description}
                    </p>
                  ) : null}
                </div>
                <Button
                  aria-label={`Xem ${evidence.title}`}
                  className="col-span-2 w-full"
                  disabled={mutation.isPending}
                  onClick={() => {
                    setActiveMediaId(evidence.mediaAssetId);
                    mutation.mutate(evidence.mediaAssetId);
                  }}
                  variant="outline"
                >
                  {opening ? (
                    <LoaderCircle className="size-4 animate-spin" />
                  ) : (
                    <ExternalLink className="size-4" />
                  )}
                  Xem bằng chứng
                </Button>
                <PrivateDocumentVerification mediaId={evidence.mediaAssetId} />
              </article>
            );
          })}
        </div>
      ) : (
        <p className="p-8 text-sm text-neutral-500">
          Phiên bản này không có tài liệu bằng chứng.
        </p>
      )}
      {mutation.isError ? (
        <p
          className="border-t border-red-200 bg-red-50 px-6 py-3 text-sm font-semibold text-red-800"
          role="alert"
        >
          Không thể tạo liên kết bảo mật cho tài liệu.
        </p>
      ) : null}
      {preview ? (
        <section
          aria-label={`Xem trước ${preview.evidence.title}`}
          className="border-t border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 sm:p-6"
          role="region"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary-700">
                Bản xem trước an toàn
              </p>
              <h3 className="mt-1 truncate font-bold">
                {preview.evidence.title}
              </h3>
              <p className="mt-1 text-xs text-neutral-500">
                Liên kết có thời hạn · chỉ dùng trong phiên làm việc này
              </p>
            </div>
            <Button
              aria-label="Đóng xem trước"
              onClick={() => setPreview(null)}
              variant="ghost"
            >
              <X aria-hidden="true" className="size-4" />
            </Button>
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-[var(--theme-border)] bg-black/5">
            {preview.evidence.media.mimeType.startsWith("image/") ? (
              // Signed review media can use storage hosts not known at build time.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={preview.evidence.title}
                className="max-h-[65vh] w-full object-contain"
                src={preview.url}
              />
            ) : preview.evidence.media.mimeType === "application/pdf" ? (
              <iframe
                className="h-[65vh] min-h-96 w-full bg-white"
                src={preview.url}
                title={`PDF ${preview.evidence.title}`}
              />
            ) : preview.evidence.media.mimeType.startsWith("audio/") ? (
              <div className="grid min-h-44 place-items-center p-6">
                <audio className="w-full" controls src={preview.url}>
                  Trình duyệt không hỗ trợ phát tệp âm thanh này.
                </audio>
              </div>
            ) : preview.evidence.media.mimeType.startsWith("video/") ? (
              <video
                className="max-h-[65vh] w-full bg-black"
                controls
                src={preview.url}
              >
                Trình duyệt không hỗ trợ phát tệp video này.
              </video>
            ) : (
              <div className="grid min-h-44 place-items-center gap-3 p-6 text-center">
                <FileText
                  aria-hidden="true"
                  className="size-8 text-neutral-500"
                />
                <div>
                  <p className="font-bold">
                    Định dạng cần mở bằng ứng dụng phù hợp
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    Nội dung không được nhúng trực tiếp để tránh làm sai định dạng hoặc giảm an toàn.
                  </p>
                </div>
              </div>
            )}
          </div>
          <a
            className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-bold"
            href={preview.url}
            rel="noopener noreferrer"
            target="_blank"
          >
            {preview.evidence.media.mimeType.startsWith("image/") ||
            preview.evidence.media.mimeType === "application/pdf" ? (
              <ExternalLink aria-hidden="true" className="size-4" />
            ) : (
              <Download aria-hidden="true" className="size-4" />
            )}
            Mở tệp trong tab mới
          </a>
        </section>
      ) : null}
    </Card>
  );
}
