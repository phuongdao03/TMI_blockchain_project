"use client";

import {
  CircleAlert,
  FileCheck2,
  FileImage,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import {
  type ChangeEvent,
  type DragEvent,
  useId,
  useRef,
  useState,
} from "react";

import {
  type UploadStatus,
  useMediaUploader,
} from "@/components/media/use-media-uploader";
import { FileUploaderActions } from "@/components/media/file-uploader-actions";
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

const statusText: Record<UploadStatus, string> = {
  inspecting: "Đang kiểm tra an toàn tệp…",
  idle: "Chưa chọn tệp",
  selected: "Sẵn sàng tải lên",
  signing: "Đang tạo chữ ký bảo mật…",
  uploading: "Đang tải lên Cloudinary",
  verifying: "Đang xác minh tệp…",
  complete: "Tệp đã được tải lên và xác minh.",
  failed: "Tải tệp chưa thành công.",
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
    error,
    file,
    files,
    isBusy,
    progress,
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

  const openPicker = () => inputRef.current?.click();
  const descriptionId = `${inputId}-description`;
  const statusLabel =
    status === "uploading"
      ? `${statusText.uploading} · ${progress}%`
      : statusText[status];

  return (
    <section aria-labelledby={`${inputId}-label`} className="space-y-3">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h3
            className="text-sm font-semibold text-neutral-950"
            id={`${inputId}-label`}
          >
            {label}
          </h3>
          <p
            className="mt-1 text-xs leading-5 text-neutral-500"
            id={descriptionId}
          >
            Tối đa {formatBytes(maxBytes)}
            {supportedFormats ? ` · ${supportedFormats}` : ""}
          </p>
        </div>
        <ShieldCheck aria-hidden="true" className="size-5 text-success" />
      </div>

      <div
        aria-label={`Vùng tải ${label.toLocaleLowerCase("vi")}`}
        className={cn(
          "rounded-xl border border-dashed p-4 transition-colors",
          isDragging
            ? "border-primary-600 bg-primary-50"
            : "border-neutral-200 bg-neutral-50",
          disabled && "opacity-60",
        )}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!isBusy && !disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        role="group"
      >
        <input
          accept={allowedMimeTypes.join(",") || policy.accept}
          aria-describedby={descriptionId}
          aria-label={`Chọn ${label.toLocaleLowerCase("vi")}`}
          className="sr-only"
          disabled={disabled || isBusy}
          id={inputId}
          multiple={multiple}
          onChange={handleInput}
          ref={inputRef}
          tabIndex={-1}
          type="file"
        />

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <span className="grid size-11 shrink-0 place-items-center rounded-lg bg-white text-primary-600 shadow-sm">
            {status === "complete" ? (
              <FileCheck2 aria-hidden="true" className="size-5" />
            ) : file ? (
              <FileImage aria-hidden="true" className="size-5" />
            ) : (
              <UploadCloud aria-hidden="true" className="size-5" />
            )}
          </span>
          <div className="min-w-0 flex-1">
            {files.length ? (
              <ul className="space-y-1 text-sm font-semibold text-neutral-950">
                {files.map((selectedFile) => (
                  <li
                    className="truncate"
                    key={`${selectedFile.name}-${selectedFile.size}`}
                  >
                    {selectedFile.name}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="truncate text-sm font-semibold text-neutral-950">
                Kéo tệp vào đây hoặc chọn từ thiết bị
              </p>
            )}
            <p
              aria-live="polite"
              className="mt-1 text-xs text-neutral-500"
              role="status"
            >
              {files.length > 1
                ? `${files.length} tệp · `
                : file
                  ? `${formatBytes(file.size)} · `
                  : ""}
              {statusLabel}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <FileUploaderActions
              disabled={disabled}
              hasFile={Boolean(file)}
              isBusy={isBusy}
              onChoose={openPicker}
              onUpload={() => void startUpload()}
              status={status}
            />
          </div>
        </div>

        {status === "uploading" ? (
          <progress
            aria-label="Tiến độ tải tệp"
            className="mt-4 h-2 w-full accent-primary-600"
            max={100}
            value={progress}
          />
        ) : null}
      </div>

      {error ? (
        <p
          className="flex items-start gap-2 text-sm font-medium text-error"
          role="alert"
        >
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : null}
    </section>
  );
}
