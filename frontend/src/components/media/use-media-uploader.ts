"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { ApiError, mediaApi } from "@/lib/api/client";
import type {
  MediaAsset,
  MediaPurpose,
  MediaUploadCompletion,
} from "@/lib/api/types";
import {
  type MediaFileConstraints,
  createMediaUploadSessionId,
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
  completion: MediaUploadCompletion | null;
  error: string | null;
  file: File;
  id: string;
  inspectionStartedAt: number | null;
  progress: number;
  status: Exclude<UploadStatus, "idle" | "complete">;
  uploadSessionId: string;
}

interface UseMediaUploaderOptions {
  cleanupCompletedOnRemove: boolean;
  constraints?: MediaFileConstraints;
  disabled: boolean;
  existingFiles?: readonly {
    filename: string | null | undefined;
    bytes: number;
    mimeType: string;
  }[];
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

function fileKey(file: File): string {
  return [
    file.name.toLocaleLowerCase("en"),
    file.size,
    file.type,
    file.lastModified,
  ].join("\u0000");
}

function uploadErrorMessage(error: unknown, canResume: boolean): string {
  if (
    (error instanceof ApiError &&
      error.code === "MEDIA_PROVIDER_UNAVAILABLE") ||
    (error instanceof Error &&
      error.message === "Media provider is unavailable.")
  ) {
    return canResume
      ? "Dịch vụ lưu trữ tạm gián đoạn. Tệp đã được gửi; bấm Thử lại để tiếp tục xác nhận, không cần tải lại."
      : "Dịch vụ lưu trữ tạm gián đoạn. Vui lòng thử lại sau ít phút.";
  }
  return error instanceof Error
    ? error.message
    : "Không thể tải tệp. Vui lòng kiểm tra kết nối và thử lại.";
}

export function useMediaUploader({
  cleanupCompletedOnRemove,
  constraints,
  disabled,
  existingFiles = [],
  maxFiles,
  onComplete,
  purpose,
}: UseMediaUploaderOptions) {
  const nextId = useRef(0);
  const activeAbortController = useRef<AbortController | null>(null);
  const processingRef = useRef(false);
  const completedFileKeys = useRef(new Set<string>());
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
      if (!nextFiles.length || processingRef.current || disabled) return;

      const seenKeys = new Set(items.map((item) => fileKey(item.file)));
      const additions: File[] = [];
      let duplicateCount = 0;
      for (const file of nextFiles) {
        const key = fileKey(file);
        const alreadyAttached = existingFiles.some(
          (existing) =>
            existing.filename?.toLocaleLowerCase("en") ===
              file.name.toLocaleLowerCase("en") &&
            existing.bytes === file.size &&
            existing.mimeType.toLocaleLowerCase("en") ===
              file.type.toLocaleLowerCase("en"),
        );
        if (
          seenKeys.has(key) ||
          completedFileKeys.current.has(key) ||
          alreadyAttached
        ) {
          duplicateCount += 1;
          continue;
        }
        seenKeys.add(key);
        additions.push(file);
      }
      if (additions.length === 0) {
        setSelectionError("Tệp này đã có trong danh sách hồ sơ.");
        return;
      }

      const available =
        maxFiles === undefined
          ? Number.POSITIVE_INFINITY
          : maxFiles - items.length;
      if (additions.length > available) {
        setSelectionError(
          available > 0
            ? `Bạn chỉ có thể thêm ${available} tệp nữa.`
            : "Đã đạt số lượng tệp tối đa cho mục này.",
        );
        return;
      }

      try {
        additions.forEach((file) =>
          validateMediaFile(file, purpose, constraints),
        );
      } catch (error) {
        setSelectionError(
          error instanceof Error ? error.message : "Tệp đã chọn không hợp lệ.",
        );
        return;
      }

      const queueItems = additions.map<UploadQueueItem>((file) => ({
        completion: null,
        error: null,
        file,
        id: `upload-${nextId.current++}`,
        inspectionStartedAt: null,
        progress: 0,
        status: "selected",
        uploadSessionId: createMediaUploadSessionId(),
      }));
      setItems((current) => [...current, ...queueItems]);
      setSelectionError(
        duplicateCount > 0 ? "Tệp đã có trong hồ sơ nên được bỏ qua." : null,
      );
      setCompletedCount(0);
    },
    [constraints, disabled, existingFiles, items, maxFiles, purpose],
  );

  const selectFile = useCallback(
    (file: File | undefined) => selectFiles(file ? [file] : []),
    [selectFiles],
  );

  const removeFile = useCallback(
    async (id: string) => {
      if (processingRef.current || disabled) return;
      const item = items.find((candidate) => candidate.id === id);
      if (cleanupCompletedOnRemove && item?.completion) {
        try {
          await mediaApi.deleteAsset(item.completion.mediaId);
        } catch {
          setSelectionError(
            "Chưa xóa được tệp đã tải lên. Hãy thử lại hoặc giữ tệp trong danh sách đã chọn.",
          );
          return;
        }
      }
      setItems((current) => current.filter((item) => item.id !== id));
      setSelectionError(null);
    },
    [cleanupCompletedOnRemove, disabled, items],
  );

  const startUpload = useCallback(async () => {
    if (processingRef.current || disabled) return;
    const pending = items.filter(
      (item) => item.status === "selected" || item.status === "failed",
    );
    if (!pending.length) return;

    processingRef.current = true;
    setIsProcessing(true);
    setSelectionError(null);
    let newlyCompleted = 0;

    for (const queued of pending) {
      let completion = queued.completion;
      const controller = new AbortController();
      activeAbortController.current = controller;
      updateItem(queued.id, {
        error: null,
        inspectionStartedAt: null,
        progress: completion ? 100 : 0,
        status: completion ? "verifying" : "signing",
      });
      try {
        const asset = await uploadMedia(
          queued.file,
          purpose,
          {
            onProgress: (progress) => updateItem(queued.id, { progress }),
            onStage: (status) =>
              updateItem(queued.id, {
                status,
                inspectionStartedAt:
                  status === "inspecting" ? Date.now() : null,
              }),
            onTransferred: (transferred) => {
              completion = transferred;
              updateItem(queued.id, { completion: transferred, progress: 100 });
            },
            resumeCompletion: completion ?? undefined,
            uploadSessionId: queued.uploadSessionId,
            signal: controller.signal,
          },
          constraints,
        );
        await onComplete(asset, newlyCompleted);
        newlyCompleted += 1;
        completedFileKeys.current.add(fileKey(queued.file));
        setItems((current) => current.filter((item) => item.id !== queued.id));
      } catch (error) {
        updateItem(queued.id, {
          completion,
          error: uploadErrorMessage(error, completion !== null),
          status: "failed",
        });
      }
      activeAbortController.current = null;
    }

    if (newlyCompleted > 0) {
      setCompletedCount((current) => current + newlyCompleted);
    }
    processingRef.current = false;
    setIsProcessing(false);
  }, [constraints, disabled, items, onComplete, purpose, updateItem]);

  const failedCount = items.filter((item) => item.status === "failed").length;
  const pendingCount = items.filter(
    (item) => item.status === "selected" || item.status === "failed",
  ).length;
  const activeItem = items.find((item) => BUSY_STATUSES.includes(item.status));
  const stopWaiting = useCallback(
    () => activeAbortController.current?.abort(),
    [],
  );
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
    stopWaiting,
    status,
  };
}
