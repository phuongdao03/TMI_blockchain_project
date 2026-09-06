import { z } from "zod";

import { mediaApi } from "@/lib/api/client";
import type {
  MediaAsset,
  MediaPurpose,
  MediaUploadAuthorization,
} from "@/lib/api/types";

type UploadStage = "uploading" | "verifying" | "inspecting";

interface UploadCallbacks {
  inspectionPollIntervalMs?: number;
  onProgress?: (progress: number) => void;
  onStage?: (stage: UploadStage) => void;
}

/**
 * Server-owned dossier document rules passed to the browser for early feedback.
 * The upload signature and the dossier API remain authoritative.
 */
export interface MediaFileConstraints {
  allowedMimeTypes?: readonly string[];
  maxBytes?: number;
}

const DEFAULT_INSPECTION_POLL_INTERVAL_MS = 1_500;
const MAX_INSPECTION_POLLS = 40;

const wait = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

async function waitForInspection(
  mediaId: string,
  intervalMs: number,
): Promise<MediaAsset> {
  for (let attempt = 0; attempt < MAX_INSPECTION_POLLS; attempt += 1) {
    const asset = await mediaApi.getAsset(mediaId);
    if (asset.status === "ACTIVE") {
      return asset;
    }
    if (asset.status === "REJECTED") {
      throw new Error(
        "Tệp không vượt qua bước xác minh an toàn. Vui lòng chọn tệp khác.",
      );
    }
    if (asset.status !== "PENDING" && asset.status !== "QUARANTINED") {
      throw new Error("Tệp không còn ở trạng thái có thể xử lý.");
    }
    await wait(intervalMs);
  }
  throw new Error(
    "Việc kiểm tra tệp đang mất nhiều thời gian hơn dự kiến. Vui lòng thử lại sau.",
  );
}

interface MediaPolicy {
  accept: string;
  maxBytes: number;
  maxMegabytes: number;
  formats: Readonly<Record<string, readonly string[]>>;
}

export const mediaPolicies: Record<MediaPurpose, MediaPolicy> = {
  AVATAR: {
    accept: "image/jpeg,image/png,image/webp",
    maxBytes: 5_242_880,
    maxMegabytes: 5,
    formats: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
    },
  },
  DOSSIER_EVIDENCE: {
    accept:
      "image/jpeg,image/png,image/webp,application/pdf,audio/mpeg,audio/mp4,audio/ogg,audio/wav,audio/x-wav,video/mp4,video/webm,application/msword,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/zip",
    maxBytes: 104_857_600,
    maxMegabytes: 100,
    formats: {
      "application/pdf": [".pdf"],
      "application/msword": [".doc"],
      "application/vnd.ms-excel": [".xls"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
        ".xlsx",
      ],
      "application/zip": [".zip"],
      "audio/mpeg": [".mp3"],
      "audio/mp4": [".m4a", ".mp4"],
      "audio/ogg": [".ogg"],
      "audio/wav": [".wav"],
      "audio/x-wav": [".wav"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
      "video/mp4": [".mp4"],
      "video/webm": [".webm"],
    },
  },
  PUBLIC_WORK: {
    accept:
      "image/jpeg,image/png,image/webp,application/pdf,audio/mpeg,audio/mp4,audio/ogg,video/mp4,video/webm",
    maxBytes: 20_971_520,
    maxMegabytes: 20,
    formats: {
      "application/pdf": [".pdf"],
      "audio/mpeg": [".mp3"],
      "audio/mp4": [".m4a", ".mp4"],
      "audio/ogg": [".ogg"],
      "audio/wav": [".wav"],
      "audio/x-wav": [".wav"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
      "video/mp4": [".mp4"],
      "video/webm": [".webm"],
    },
  },
};

const cloudinaryResponseSchema = z.object({
  public_id: z.string().min(1),
  signature: z.string().regex(/^[a-fA-F0-9]{40}$/),
  version: z.number().int().nonnegative(),
});

export class MediaUploadValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MediaUploadValidationError";
  }
}

export function validateMediaFile(
  file: File,
  purpose: MediaPurpose,
  constraints?: MediaFileConstraints,
): void {
  const policy = mediaPolicies[purpose];
  const extensions = policy.formats[file.type];
  if (!extensions) {
    throw new MediaUploadValidationError(
      "Định dạng tệp không được hỗ trợ cho mục đích này.",
    );
  }
  if (file.size <= 0) {
    throw new MediaUploadValidationError("Tệp không được để trống.");
  }
  if (
    constraints?.allowedMimeTypes?.length &&
    !constraints.allowedMimeTypes.includes(file.type)
  ) {
    throw new MediaUploadValidationError(
      "Định dạng tệp không phù hợp với loại tài liệu đã chọn.",
    );
  }
  const maxBytes = constraints?.maxBytes ?? policy.maxBytes;
  if (file.size > maxBytes) {
    throw new MediaUploadValidationError(
      `Tệp vượt quá giới hạn ${formatMegabytes(maxBytes)} MB.`,
    );
  }
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!extensions.includes(extension)) {
    throw new MediaUploadValidationError(
      "Phần mở rộng của tệp không khớp với định dạng đã chọn.",
    );
  }
}

function formatMegabytes(bytes: number): string {
  return (bytes / 1_048_576).toLocaleString("vi-VN", {
    maximumFractionDigits: 1,
  });
}

const CHUNKED_UPLOAD_THRESHOLD_BYTES = 20 * 1_048_576;
const UPLOAD_CHUNK_BYTES = 6 * 1_048_576;

function rejectedUploadMessage(status: number, response: unknown): string {
  const upstreamMessage = z
    .object({ error: z.object({ message: z.string() }) })
    .safeParse(response);
  const reason = upstreamMessage.success
    ? upstreamMessage.data.error.message.toLocaleLowerCase("en")
    : "";
  if (
    status === 413 ||
    reason.includes("file size") ||
    reason.includes("too large") ||
    reason.includes("maximum")
  ) {
    return "Tệp bị từ chối vì kích thước vượt giới hạn của hệ thống lưu trữ. Hãy nén tệp hoặc chọn tệp nhỏ hơn.";
  }
  if (status === 408 || status === 504) {
    return "Tải tệp mất quá nhiều thời gian. Vui lòng kiểm tra kết nối và thử lại.";
  }
  if (status === 429) {
    return "Hệ thống đang nhận nhiều lượt tải tệp. Vui lòng đợi một lát rồi thử lại.";
  }
  return "Dịch vụ lưu trữ chưa thể nhận tệp này. Vui lòng thử lại hoặc chọn tệp khác.";
}

function sendUploadRequest(
  content: Blob,
  filename: string,
  authorization: MediaUploadAuthorization,
  headers: Readonly<Record<string, string>>,
  onProgress?: (progress: number) => void,
): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    if (content instanceof File) form.append("file", content);
    else form.append("file", content, filename);
    form.append("api_key", authorization.apiKey);
    form.append("signature", authorization.signature);
    for (const [name, value] of Object.entries(authorization.parameters)) {
      form.append(name, value);
    }

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && event.total > 0) {
        onProgress?.(
          Math.min(100, Math.round((event.loaded / event.total) * 100)),
        );
      }
    });
    xhr.addEventListener("error", () => {
      reject(new Error("Không thể kết nối đến dịch vụ tải tệp."));
    });
    xhr.addEventListener("abort", () => {
      reject(new Error("Quá trình tải tệp đã bị hủy."));
    });
    xhr.addEventListener("timeout", () => {
      reject(new Error("Quá trình tải tệp đã hết thời gian chờ."));
    });
    xhr.addEventListener("load", () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(rejectedUploadMessage(xhr.status, xhr.response)));
        return;
      }
      resolve(xhr.response);
    });
    xhr.responseType = "json";
    xhr.timeout = 600_000;
    xhr.open("POST", authorization.uploadUrl, true);
    for (const [name, value] of Object.entries(headers)) {
      xhr.setRequestHeader(name, value);
    }
    xhr.send(form);
  });
}

async function uploadToCloudinary(
  file: File,
  authorization: MediaUploadAuthorization,
  onProgress?: (progress: number) => void,
): Promise<z.infer<typeof cloudinaryResponseSchema>> {
  let response: unknown;
  if (file.size <= CHUNKED_UPLOAD_THRESHOLD_BYTES) {
    response = await sendUploadRequest(
      file,
      file.name,
      authorization,
      {},
      onProgress,
    );
  } else {
    const uploadId = crypto.randomUUID();
    for (let start = 0; start < file.size; start += UPLOAD_CHUNK_BYTES) {
      const endExclusive = Math.min(start + UPLOAD_CHUNK_BYTES, file.size);
      response = await sendUploadRequest(
        file.slice(start, endExclusive, file.type),
        file.name,
        authorization,
        {
          "Content-Range": `bytes ${start}-${endExclusive - 1}/${file.size}`,
          "X-Unique-Upload-Id": uploadId,
        },
        (chunkProgress) => {
          const uploaded =
            start + ((endExclusive - start) * chunkProgress) / 100;
          onProgress?.(Math.min(100, Math.round((uploaded / file.size) * 100)));
        },
      );
    }
  }

  const result = cloudinaryResponseSchema.safeParse(response);
  if (!result.success) {
    throw new Error("Phản hồi từ dịch vụ lưu trữ không hợp lệ.");
  }
  return result.data;
}

export async function uploadMedia(
  file: File,
  purpose: MediaPurpose,
  callbacks: UploadCallbacks = {},
  constraints?: MediaFileConstraints,
): Promise<MediaAsset> {
  validateMediaFile(file, purpose, constraints);
  const authorization = await mediaApi.createUploadSignature({
    confidentiality: purpose === "PUBLIC_WORK" ? "PUBLIC" : "PRIVATE",
    purpose,
    filename: file.name,
    mimeType: file.type,
    size: file.size,
  });
  callbacks.onStage?.("uploading");
  const result = await uploadToCloudinary(
    file,
    authorization,
    callbacks.onProgress,
  );
  if (result.public_id !== authorization.publicId) {
    throw new Error("Tệp tải lên không khớp với phiên bảo mật hiện tại.");
  }
  callbacks.onStage?.("verifying");
  const asset = await mediaApi.completeUpload({
    mediaId: authorization.mediaId,
    publicId: result.public_id,
    version: result.version,
    signature: result.signature,
  });
  if (asset.status === "ACTIVE") {
    return asset;
  }
  if (asset.status !== "QUARANTINED") {
    throw new Error("Tệp chưa hoàn tất xác minh. Vui lòng thử lại.");
  }
  callbacks.onStage?.("inspecting");
  return waitForInspection(
    asset.id,
    callbacks.inspectionPollIntervalMs ?? DEFAULT_INSPECTION_POLL_INTERVAL_MS,
  );
}
