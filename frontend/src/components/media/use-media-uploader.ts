"use client";

import { useCallback, useMemo, useRef, useState } from "react";

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

export interface UploadQueueItem {
  error: string | null;
  file: File;
  id: string;
  progress: number;
  status: Exclude<UploadStatus, "idle" | "complete">;
}

interface UseMediaUploaderOptions {
  constraints?: MediaFileConstraints;
  disabled: boolean;
  maxFiles?: number;
  onComplete: (asset: MediaAsset, index: number) => void | Promise<void>;
  purpose: MediaPurpose;
}

const BUSY_STATUSES: readonly UploadQueueItem["status"][] = [
  "signing",
  "uploading",
  "verifying",
  "inspecting",
];

function uploadErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Không thể tải tệp. Vui lòng kiểm tra kết nối và thử lại.";
}

export function useMediaUploader({
  constraints,
  disabled,
  maxFiles,
  onComplete,
  purpose,
}: UseMediaUploaderOptions) {
  const nextId = useRef(0);
  const [items, setItems] = useState<UploadQueueItem[]>([]);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [completedCount, setCompletedCount] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const updateItem = useCallback(
    (id: string, update: Partial<UploadQueueItem>) => {
      setItems((current) =>
        current.map((item) => (item.id === id ? { ...item, ...update } : item)),
      );
    },
    [],
  );

  const selectFiles = useCallback(
    (nextFiles: readonly File[]) => {
      if (!nextFiles.length || isProcessing || disabled) return;

      const available =
        maxFiles === undefined
          ? Number.POSITIVE_INFINITY
          : maxFiles - items.length;
      if (nextFiles.length > available) {
        setSelectionError(
          available > 0
            ? `Bạn chỉ có thể thêm ${available} tệp nữa.`
            : "Đã đạt số lượng tệp tối đa cho mục này.",
        );
        return;
      }

      try {
        nextFiles.forEach((file) =>
          validateMediaFile(file, purpose, constraints),
        );
      } catch (error) {
        setSelectionError(
          error instanceof Error ? error.message : "Tệp đã chọn không hợp lệ.",
        );
        return;
      }

      const additions = nextFiles.map<UploadQueueItem>((file) => ({
        error: null,
        file,
        id: `upload-${nextId.current++}`,
        progress: 0,
        status: "selected",
      }));
      setItems((current) => [...current, ...additions]);
      setSelectionError(null);
      setCompletedCount(0);
    },
    [constraints, disabled, isProcessing, items.length, maxFiles, purpose],
  );

  const selectFile = useCallback(
    (file: File | undefined) => selectFiles(file ? [file] : []),
    [selectFiles],
  );

  const removeFile = useCallback(
    (id: string) => {
      if (isProcessing || disabled) return;
      setItems((current) => current.filter((item) => item.id !== id));
      setSelectionError(null);
    },
    [disabled, isProcessing],
  );

  const startUpload = useCallback(async () => {
    if (isProcessing || disabled) return;
    const pending = items.filter(
      (item) => item.status === "selected" || item.status === "failed",
    );
    if (!pending.length) return;

    setIsProcessing(true);
    setSelectionError(null);
    let newlyCompleted = 0;

    for (const queued of pending) {
      updateItem(queued.id, {
        error: null,
        progress: 0,
        status: "signing",
      });
      try {
        const asset = await uploadMedia(
          queued.file,
          purpose,
          {
            onProgress: (progress) => updateItem(queued.id, { progress }),
            onStage: (status) => updateItem(queued.id, { status }),
          },
          constraints,
        );
        await onComplete(asset, newlyCompleted);
        newlyCompleted += 1;
        setItems((current) => current.filter((item) => item.id !== queued.id));
      } catch (error) {
        updateItem(queued.id, {
          error: uploadErrorMessage(error),
          status: "failed",
        });
      }
    }

    if (newlyCompleted > 0) {
      setCompletedCount((current) => current + newlyCompleted);
    }
    setIsProcessing(false);
  }, [
    constraints,
    disabled,
    isProcessing,
    items,
    onComplete,
    purpose,
    updateItem,
  ]);

  const failedCount = items.filter((item) => item.status === "failed").length;
  const pendingCount = items.filter(
    (item) => item.status === "selected" || item.status === "failed",
  ).length;
  const activeItem = items.find((item) => BUSY_STATUSES.includes(item.status));
  const status = useMemo<UploadStatus>(() => {
    if (activeItem) return activeItem.status;
    if (failedCount > 0) return "failed";
    if (items.length > 0) return "selected";
    if (completedCount > 0) return "complete";
    return "idle";
  }, [activeItem, completedCount, failedCount, items.length]);

  return {
    completedCount,
    error: selectionError,
    failedCount,
    file: items[0]?.file ?? null,
    files: items.map((item) => item.file),
    isBusy: isProcessing,
    items,
    pendingCount,
    progress: activeItem?.progress ?? (completedCount > 0 ? 100 : 0),
    removeFile,
    selectFile,
    selectFiles,
    startUpload,
    status,
  };
}
