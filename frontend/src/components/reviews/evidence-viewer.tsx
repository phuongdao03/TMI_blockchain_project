"use client";

import { useMutation } from "@tanstack/react-query";
import {
  ExternalLink,
  FileImage,
  FileText,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
  const mutation = useMutation({
    mutationFn: mediaApi.signedUrl,
    onSuccess: (delivery) => {
      window.open(delivery.url, "_blank", "noopener,noreferrer");
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
    </Card>
  );
}
