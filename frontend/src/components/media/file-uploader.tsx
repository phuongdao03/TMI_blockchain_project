"use client";

import {
  CircleAlert,
  FileCheck2,
  FileText,
  LoaderCircle,
  ShieldCheck,
  Trash2,
  Upload,
} from "lucide-react";
import {
  type ChangeEvent,
  type DragEvent,
  useId,
  useRef,
  useState,
} from "react";

import { FileUploaderActions } from "@/components/media/file-uploader-actions";
import {
  type UploadQueueItem,
  type UploadStatus,
  useMediaUploader,
} from "@/components/media/use-media-uploader";
import type { MediaAsset, MediaPurpose } from "@/lib/api/types";
import { type MediaFileConstraints, mediaPolicies } from "@/lib/media/upload";
import { cn } from "@/lib/utils";

interface FileUploaderProps {
  constraints?: MediaFileConstraints;
  disabled?: boolean;
  label: string;
  maxFiles?: number;
  multiple?: boolean;
  onComplete: (asset: MediaAsset, index: number) => void | Promise<void>;
  purpose: MediaPurpose;
}

const statusText: Record<UploadQueueItem["status"], string> = {
  failed: "Tải tệp chưa thành công",
  inspecting: "Đang kiểm tra an toàn…",
  selected: "Sẵn sàng tải lên",
  signing: "Đang chuẩn bị tải tệp…",
  uploading: "Đang tải tệp",
  verifying: "Đang xác nhận tệp…",
};

function formatBytes(bytes: number): string {
  if (bytes < 1_048_576) {
    return `${Math.max(1, Math.round(bytes / 1_024))} KB`;
  }
  return `${(bytes / 1_048_576).toLocaleString("vi-VN", {
    maximumFractionDigits: 1,
  })} MB`;
}

function supportedFormatLabel(
  mimeTypes: readonly string[],
  policy: (typeof mediaPolicies)[MediaPurpose],
): string {
  const extensions = mimeTypes.flatMap(
    (mimeType) => policy.formats[mimeType] ?? [],
  );
  return [
    ...new Set(extensions.map((extension) => extension.slice(1).toUpperCase())),
  ].join(", ");
}

function itemStatus(item: UploadQueueItem): string {
  if (item.status === "uploading") {
    return `${statusText.uploading} · ${item.progress}%`;
  }
  return statusText[item.status];
}

function overallStatus(
  status: UploadStatus,
  count: number,
  completedCount: number,
): string {
  if (status === "complete") {
    return completedCount === 1
      ? "Tệp đã được tải lên và xác minh."
      : `Đã tải lên và xác minh ${completedCount} tệp.`;
  }
  if (status === "failed") {
    return "Có tệp chưa tải thành công. Bạn có thể thử lại hoặc xóa tệp đó.";
  }
  if (status === "idle") return "Chưa chọn tệp.";
  if (count > 0 && status === "selected") {
    return `${count} tệp · Sẵn sàng tải lên.`;
  }
  return "Đang xử lý hàng đợi tải tệp.";
}

export function FileUploader({
  constraints,
  disabled = false,
  label,
  maxFiles,
  multiple = false,
  onComplete,
  purpose,
}: FileUploaderProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const policy = mediaPolicies[purpose];
  const allowedMimeTypes = constraints?.allowedMimeTypes?.length
    ? constraints.allowedMimeTypes
    : Object.keys(policy.formats);
  const maxBytes = constraints?.maxBytes ?? policy.maxBytes;
  const supportedFormats = supportedFormatLabel(allowedMimeTypes, policy);
  const {
    completedCount,
    error,
    failedCount,
    isBusy,
    items,
    pendingCount,
    removeFile,
    selectFile,
    selectFiles,
    startUpload,
    status,
  } = useMediaUploader({
    constraints,
    disabled,
    maxFiles,
    onComplete,
    purpose,
  });

  const handleInput = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []);
    if (multiple) selectFiles(selected);
    else selectFile(selected[0]);
    event.target.value = "";
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const dropped = Array.from(event.dataTransfer.files);
    if (multiple) selectFiles(dropped);
    else selectFile(dropped[0]);
  };

  const canChoose = multiple
    ? maxFiles === undefined || items.length < maxFiles
    : items.length === 0;
  const activeItem = items.find((item) =>
    ["signing", "uploading", "verifying", "inspecting"].includes(item.status),
  );
  const openPicker = () => inputRef.current?.click();
  const descriptionId = `${inputId}-description`;

  return (
    <section
      aria-labelledby={`${inputId}-label`}
      className="media-uploader overflow-hidden rounded-2xl border border-neutral-200 bg-white"
    >
      <div className="flex flex-col gap-3 border-b border-neutral-200 px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-success/10 text-success">
              <ShieldCheck aria-hidden="true" className="size-4" />
            </span>
            <h3
              className="text-base font-bold text-neutral-950"
              id={`${inputId}-label`}
            >
              {label}
            </h3>
          </div>
          <p
            className="mt-2 text-sm leading-6 text-neutral-600"
            id={descriptionId}
          >
            Mỗi tệp tối đa {formatBytes(maxBytes)}. Tệp được kiểm tra an toàn
            trước khi thêm vào hồ sơ.
          </p>
        </div>
        {maxFiles !== undefined ? (
          <span className="w-fit shrink-0 rounded-full bg-neutral-100 px-3 py-1 text-xs font-bold text-neutral-700">
            Còn {Math.max(0, maxFiles - items.length)} tệp
          </span>
        ) : null}
      </div>

      <div className="space-y-4 p-4 sm:p-5">
        <input
          accept={allowedMimeTypes.join(",") || policy.accept}
          aria-describedby={descriptionId}
          aria-label={`Chọn ${label.toLocaleLowerCase("vi")}`}
          className="sr-only"
          disabled={disabled || isBusy || !canChoose}
          id={inputId}
          multiple={multiple}
          onChange={handleInput}
          ref={inputRef}
          tabIndex={-1}
          type="file"
        />

        <div
          aria-label={`Vùng tải ${label.toLocaleLowerCase("vi")}`}
          className={cn(
            "media-uploader__dropzone rounded-xl border border-dashed p-4 sm:p-5",
            isDragging
              ? "border-primary-600 bg-primary-50"
              : "border-neutral-300 bg-neutral-50",
            disabled && "opacity-60",
          )}
          onDragEnter={(event) => {
            event.preventDefault();
            if (canChoose && !isBusy && !disabled) setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          role="group"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary-700 ring-1 ring-primary-100">
              <Upload aria-hidden="true" className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-bold text-neutral-950">
                {items.length
                  ? "Bạn có thể tiếp tục thêm tệp"
                  : multiple
                    ? "Chọn một hoặc nhiều tệp"
                    : "Chọn tệp từ thiết bị"}
              </p>
              <p className="mt-1 text-xs leading-5 text-neutral-500">
                Kéo thả vào đây hoặc dùng nút Thêm tệp. Hỗ trợ:{" "}
                {supportedFormats}.
              </p>
            </div>
            <FileUploaderActions
              canChoose={canChoose}
              disabled={disabled}
              failedCount={failedCount}
              isBusy={isBusy}
              onChoose={openPicker}
              onUpload={() => void startUpload()}
              pendingCount={pendingCount}
            />
          </div>
        </div>

        {items.length ? (
          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-sm font-bold text-neutral-950">
                Tệp đang chờ ({items.length})
              </p>
              <p className="text-xs text-neutral-500">
                Có thể thêm nhiều lần trước khi tải
              </p>
            </div>
            <ul className="space-y-2">
              {items.map((item) => {
                const hasError = item.status === "failed";
                const isItemBusy = [
                  "signing",
                  "uploading",
                  "verifying",
                  "inspecting",
                ].includes(item.status);
                return (
                  <li
                    className={cn(
                      "media-uploader__item rounded-xl border bg-white p-3",
                      hasError
                        ? "border-error/40 bg-error/5"
                        : "border-neutral-200",
                    )}
                    key={item.id}
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className="t-icon-swap mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-neutral-100 text-neutral-700"
                        data-state={item.status === "selected" ? "a" : "b"}
                      >
                        <span className="t-icon" data-icon="a">
                          <FileText aria-hidden="true" className="size-4" />
                        </span>
                        <span className="t-icon" data-icon="b">
                          {hasError ? (
                            <CircleAlert
                              aria-hidden="true"
                              className="size-4 text-error"
                            />
                          ) : (
                            <LoaderCircle
                              aria-hidden="true"
                              className="size-4 animate-spin text-primary-700"
                            />
                          )}
                        </span>
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-bold text-neutral-950">
                          {item.file.name}
                        </p>
                        <p className="mt-0.5 text-xs text-neutral-500">
                          {formatBytes(item.file.size)} · {itemStatus(item)}
                        </p>
                        {item.status === "uploading" ? (
                          <progress
                            aria-label={`Tiến độ tải ${item.file.name}`}
                            className="media-uploader__progress mt-2 h-1.5 w-full accent-primary-600"
                            max={100}
                            value={item.progress}
                          />
                        ) : null}
                        {item.error ? (
                          <p
                            className="mt-2 text-xs font-semibold leading-5 text-error"
                            role="alert"
                          >
                            {item.error}
                          </p>
                        ) : null}
                      </div>
                      {!isBusy && !isItemBusy ? (
                        <button
                          aria-label={`Xóa ${item.file.name}`}
                          className="grid size-9 shrink-0 place-items-center rounded-lg text-neutral-500 transition-colors hover:bg-error/10 hover:text-error focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
                          onClick={() => removeFile(item.id)}
                          type="button"
                        >
                          <Trash2 aria-hidden="true" className="size-4" />
                        </button>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}

        <p
          aria-live="polite"
          className={cn(
            "flex items-center gap-2 text-sm font-medium",
            status === "complete" ? "text-success" : "text-neutral-600",
          )}
          role="status"
        >
          {status === "complete" ? (
            <FileCheck2 aria-hidden="true" className="size-4 shrink-0" />
          ) : null}
          {activeItem
            ? itemStatus(activeItem)
            : overallStatus(status, items.length, completedCount)}
        </p>

        {error ? (
          <p
            className="media-uploader__error flex items-start gap-2 rounded-xl border border-error/30 bg-error/5 p-3 text-sm font-medium text-error"
            role="alert"
          >
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
