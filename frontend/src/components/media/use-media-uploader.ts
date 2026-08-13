"use client";

import { useCallback, useState } from "react";

import type { MediaAsset, MediaPurpose } from "@/lib/api/types";
import { uploadMedia, validateMediaFile } from "@/lib/media/upload";

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
  disabled: boolean;
  onComplete: (asset: MediaAsset) => void;
  purpose: MediaPurpose;
}

export function useMediaUploader({
  disabled,
  onComplete,
  purpose,
}: UseMediaUploaderOptions) {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const isBusy = ["signing", "uploading", "verifying", "inspecting"].includes(
    status,
  );

  const selectFile = useCallback(
    (nextFile: File | undefined) => {
      if (!nextFile || isBusy || disabled) {
        return;
      }
      try {
        validateMediaFile(nextFile, purpose);
        setFile(nextFile);
        setStatus("selected");
        setProgress(0);
        setError(null);
      } catch (validationError) {
        setFile(null);
        setStatus("failed");
        setProgress(0);
        setError(
          validationError instanceof Error
            ? validationError.message
            : "Tệp đã chọn không hợp lệ.",
        );
      }
    },
    [disabled, isBusy, purpose],
  );

  const startUpload = useCallback(async () => {
    if (!file || isBusy || disabled) {
      return;
    }
    setStatus("signing");
    setProgress(0);
    setError(null);
    try {
      const asset = await uploadMedia(file, purpose, {
        onProgress: setProgress,
        onStage: setStatus,
      });
      setProgress(100);
      setStatus("complete");
      onComplete(asset);
    } catch (uploadError) {
      setStatus("failed");
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Không thể tải tệp. Vui lòng thử lại.",
      );
    }
  }, [disabled, file, isBusy, onComplete, purpose]);

  return {
    error,
    file,
    isBusy,
    progress,
    selectFile,
    startUpload,
    status,
  };
}
