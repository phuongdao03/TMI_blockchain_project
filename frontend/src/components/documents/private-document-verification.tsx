"use client";

import { useMutation } from "@tanstack/react-query";
import {
  CircleAlert,
  FileCheck2,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { mediaApi } from "@/lib/api/client";
import type { DocumentVerificationStatus } from "@/lib/api/types";

const MAX_VERIFICATION_BYTES = 25 * 1024 * 1024;

const statusCopy: Record<
  DocumentVerificationStatus,
  { title: string; detail: string; tone: string }
> = {
  MATCH: {
    title: "Bản tài liệu trùng khớp",
    detail: "Nội dung khớp với bằng chứng đã được xác nhận.",
    tone: "text-emerald-700",
  },
  NO_MATCH: {
    title: "Bản tài liệu không trùng khớp",
    detail:
      "Hãy chọn đúng bản đã gửi hoặc liên hệ hỗ trợ nếu bạn cần kiểm tra.",
    tone: "text-red-700",
  },
  PENDING_CONFIRMATION: {
    title: "Bằng chứng đang được hoàn tất",
    detail: "Vui lòng thử lại sau khi quá trình phát hành hoàn thành.",
    tone: "text-amber-700",
  },
  CHAIN_UNAVAILABLE: {
    title: "Tạm thời chưa thể xác nhận",
    detail:
      "Dịch vụ xác nhận đang gián đoạn. Tài liệu của bạn không được lưu lại.",
    tone: "text-amber-700",
  },
  NOT_FOUND: {
    title: "Không thể kiểm tra tài liệu này",
    detail: "Kiểm tra lại hồ sơ hoặc liên hệ hỗ trợ nếu bạn cần trợ giúp.",
    tone: "text-neutral-700",
  },
  NOT_AUTHORIZED: {
    title: "Không thể kiểm tra tài liệu này",
    detail: "Kiểm tra lại hồ sơ hoặc liên hệ hỗ trợ nếu bạn cần trợ giúp.",
    tone: "text-neutral-700",
  },
};

export function PrivateDocumentVerification({ mediaId }: { mediaId: string }) {
  const [clientError, setClientError] = useState<string | null>(null);
  const previousMediaId = useRef(mediaId);
  const verification = useMutation({
    mutationFn: (file: File) => mediaApi.verifyDocument(mediaId, file),
  });

  useEffect(() => {
    if (previousMediaId.current !== mediaId) {
      previousMediaId.current = mediaId;
      verification.reset();
      setClientError(null);
    }
  }, [mediaId, verification]);

  const copy = verification.data ? statusCopy[verification.data.status] : null;
  return (
    <div className="col-span-full min-w-0">
      <div className="flex flex-wrap items-center gap-3 border-t border-neutral-100 pt-3">
        <label className="inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border border-neutral-200 px-3 text-xs font-bold text-neutral-700 hover:bg-neutral-50">
          <ShieldCheck aria-hidden="true" className="size-4" />
          Kiểm tra bản lưu
          <input
            aria-label="Chọn bản tài liệu để kiểm tra"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              verification.reset();
              if (file.size === 0 || file.size > MAX_VERIFICATION_BYTES) {
                setClientError("Tệp phải có nội dung và không vượt quá 25 MB.");
                return;
              }
              setClientError(null);
              verification.mutate(file);
              event.currentTarget.value = "";
            }}
            type="file"
          />
        </label>
        <span className="text-xs text-neutral-500">
          Tệp chỉ được đọc để đối chiếu và không được lưu lại.
        </span>
      </div>
      <div aria-live="polite" className="mt-2 text-xs">
        {verification.isPending ? (
          <p className="flex items-center gap-2 text-neutral-600" role="status">
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            Đang kiểm tra…
          </p>
        ) : clientError ? (
          <p className="flex items-center gap-2 text-red-700" role="alert">
            <CircleAlert aria-hidden="true" className="size-4" /> {clientError}
          </p>
        ) : verification.error ? (
          <p className="text-red-700" role="alert">
            Chưa thể kiểm tra lúc này. Vui lòng thử lại sau.
          </p>
        ) : copy ? (
          <div className={copy.tone}>
            <p className="flex items-center gap-2 font-bold">
              <FileCheck2 aria-hidden="true" className="size-4" /> {copy.title}
            </p>
            <p className="mt-1 text-neutral-500">{copy.detail}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
