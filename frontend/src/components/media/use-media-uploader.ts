"use client";

import { useCallback, useState } from "react";

import type { MediaAsset, MediaPurpose } from "@/lib/api/types";
import {
  type MediaFileConstraints,
  uploadMedia,
  validateMediaFile,
} from "@/lib/media/upload";

export type UploadStatus =
  | "idle"
  | "selected"
  | "signing"
  | "uploading"
  | "verifying"
  | "inspecting"
  | "complete"
  | "failed";

interface UseMediaUploaderOptions {
  constraints?: MediaFileConstraints;
  disabled: boolean;
  maxFiles?: number;
  onComplete: (asset: MediaAsset, index: number) => void | Promise<void>;
  purpose: MediaPurpose;
}

export function useMediaUploader({
  constraints,
  disabled,
  maxFiles,
  onComplete,
  purpose,
}: UseMediaUploaderOptions) {
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const isBusy = ["signing", "uploading", "verifying", "inspecting"].includes(
    status,
  );

  const selectFiles = useCallback(
    (nextFiles: readonly File[]) => {
      if (!nextFiles.length || isBusy || disabled) {
        return;
      }
      try {
        if (maxFiles !== undefined && nextFiles.length > maxFiles) {
          throw new Error(`Chỉ có thể chọn tối đa ${maxFiles} tệp.`);
        }
        nextFiles.forEach((nextFile) =>
          validateMediaFile(nextFile, purpose, constraints),
        );
        setFiles([...nextFiles]);
        setStatus("selected");
        setProgress(0);
        setError(null);
      } catch (validationError) {
        setFiles([]);
        setStatus("failed");
        setProgress(0);
        setError(
          validationError instanceof Error
            ? validationError.message
            : "Tệp đã chọn không hợp lệ.",
        );
      }
    },
    [constraints, disabled, isBusy, maxFiles, purpose],
  );
  const selectFile = useCallback(
    (nextFile: File | undefined) => selectFiles(nextFile ? [nextFile] : []),
    [selectFiles],
  );

  const startUpload = useCallback(async () => {
    if (!files.length || isBusy || disabled) {
      return;
    }
    setStatus("signing");
    setProgress(0);
    setError(null);
    try {
      for (const [index, file] of files.entries()) {
        const asset = await uploadMedia(
          file,
          purpose,
          {
            onProgress: (fileProgress) => {
              setProgress(
                Math.round(((index + fileProgress / 100) / files.length) * 100),
              );
            },
            onStage: setStatus,
          },
          constraints,
        );
        await onComplete(asset, index);
      }
      setProgress(100);
      setStatus("complete");
    } catch (uploadError) {
      setStatus("failed");
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Không thể tải tệp. Vui lòng thử lại.",
      );
    }
  }, [constraints, disabled, files, isBusy, onComplete, purpose]);

  return {
    error,
    file: files[0] ?? null,
    files,
    isBusy,
    progress,
    selectFile,
    selectFiles,
    startUpload,
    status,
  };
}
