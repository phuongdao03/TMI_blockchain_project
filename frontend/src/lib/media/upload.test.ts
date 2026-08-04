import { beforeEach, describe, expect, it, vi } from "vitest";

import { mediaApi } from "@/lib/api/client";
import type { MediaAsset, MediaUploadAuthorization } from "@/lib/api/types";
import {
  MediaUploadValidationError,
  uploadMedia,
  validateMediaFile,
} from "@/lib/media/upload";

const authorization: MediaUploadAuthorization = {
  mediaId: "6a0bb388-3c26-4417-aed8-3ca05c212d1f",
  publicId:
    "ip-certificate/local/owner/avatar/6a0bb388-3c26-4417-aed8-3ca05c212d1f",
  uploadUrl: "https://api.cloudinary.test/v1_1/demo/image/upload",
  cloudName: "demo",
  apiKey: "public-api-key",
  signature: "a".repeat(40),
  parameters: {
    allowed_formats: "png",
    overwrite: "false",
    public_id:
      "ip-certificate/local/owner/avatar/6a0bb388-3c26-4417-aed8-3ca05c212d1f",
    timestamp: "1785398400",
    type: "authenticated",
  },
  expiresAt: 1_785_402_000,
};

const activeAsset: MediaAsset = {
  id: authorization.mediaId,
  status: "ACTIVE",
  mimeType: "image/png",
  bytes: 2_048,
  width: 512,
  height: 512,
  durationMs: null,
};

class FakeXMLHttpRequest extends EventTarget {
  static latest: FakeXMLHttpRequest | undefined;
  static response: unknown = {
    public_id: authorization.publicId,
    version: 17,
    signature: "b".repeat(40),
  };

  readonly upload = new EventTarget();
  readonly open = vi.fn();
  readonly sent = vi.fn();
  response: unknown = FakeXMLHttpRequest.response;
  responseType: XMLHttpRequestResponseType = "";
  status = 200;

  constructor() {
    super();
    FakeXMLHttpRequest.latest = this;
  }

  send(body: Document | XMLHttpRequestBodyInit | null) {
    this.sent(body);
    this.upload.dispatchEvent(
      new ProgressEvent("progress", {
        lengthComputable: true,
        loaded: 1_024,
        total: 2_048,
      }),
    );
    queueMicrotask(() => this.dispatchEvent(new Event("load")));
  }
}

function sizedFile(name: string, type: string, size: number) {
  const file = new File(["content"], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

describe("media upload policy", () => {
  it("rejects disallowed MIME, excessive size and mismatched extension", () => {
    expect(() =>
      validateMediaFile(
        sizedFile("document.pdf", "application/pdf", 2_048),
        "AVATAR",
      ),
    ).toThrow(MediaUploadValidationError);
    expect(() =>
      validateMediaFile(
        sizedFile("avatar.png", "image/png", 5_242_881),
        "AVATAR",
      ),
    ).toThrow(/5 MB/);
    expect(() =>
      validateMediaFile(sizedFile("avatar.jpg", "image/png", 2_048), "AVATAR"),
    ).toThrow(/phần mở rộng/i);
  });
});

describe("uploadMedia", () => {
  beforeEach(() => {
    FakeXMLHttpRequest.latest = undefined;
    FakeXMLHttpRequest.response = {
      public_id: authorization.publicId,
      version: 17,
      signature: "b".repeat(40),
    };
    vi.restoreAllMocks();
    vi.stubGlobal(
      "XMLHttpRequest",
      FakeXMLHttpRequest as unknown as typeof XMLHttpRequest,
    );
  });

  it("uploads signed form data with progress then completes verification", async () => {
    const signatureSpy = vi
      .spyOn(mediaApi, "createUploadSignature")
      .mockResolvedValue(authorization);
    const completeSpy = vi
      .spyOn(mediaApi, "completeUpload")
      .mockResolvedValue(activeAsset);
    const onProgress = vi.fn();
    const onStage = vi.fn();
    const file = sizedFile("avatar.png", "image/png", 2_048);

    await expect(
      uploadMedia(file, "AVATAR", { onProgress, onStage }),
    ).resolves.toEqual(activeAsset);

    expect(signatureSpy).toHaveBeenCalledWith({
      purpose: "AVATAR",
      filename: "avatar.png",
      mimeType: "image/png",
      size: 2_048,
    });
    expect(onStage.mock.calls.map(([stage]) => stage)).toEqual([
      "uploading",
      "verifying",
    ]);
    expect(onProgress).toHaveBeenCalledWith(50);

    const xhr = FakeXMLHttpRequest.latest;
    expect(xhr?.open).toHaveBeenCalledWith(
      "POST",
      authorization.uploadUrl,
      true,
    );
    const body = xhr?.sent.mock.calls[0]?.[0];
    expect(body).toBeInstanceOf(FormData);
    const form = body as FormData;
    expect(form.get("file")).toBe(file);
    expect(form.get("api_key")).toBe("public-api-key");
    expect(form.get("signature")).toBe("a".repeat(40));
    expect(form.get("public_id")).toBe(authorization.publicId);
    expect(completeSpy).toHaveBeenCalledWith({
      mediaId: authorization.mediaId,
      publicId: authorization.publicId,
      version: 17,
      signature: "b".repeat(40),
    });
  });

  it("rejects an invalid Cloudinary response before completion", async () => {
    vi.spyOn(mediaApi, "createUploadSignature").mockResolvedValue(
      authorization,
    );
    const completeSpy = vi.spyOn(mediaApi, "completeUpload");
    FakeXMLHttpRequest.response = {
      public_id: authorization.publicId,
      version: "invalid",
    };

    await expect(
      uploadMedia(sizedFile("avatar.png", "image/png", 2_048), "AVATAR"),
    ).rejects.toThrow(/Cloudinary/i);
    expect(completeSpy).not.toHaveBeenCalled();
  });

  it("does not complete when Cloudinary returns another public asset", async () => {
    vi.spyOn(mediaApi, "createUploadSignature").mockResolvedValue(
      authorization,
    );
    const completeSpy = vi.spyOn(mediaApi, "completeUpload");
    FakeXMLHttpRequest.response = {
      public_id: "another-owner/avatar",
      version: 17,
      signature: "b".repeat(40),
    };

    await expect(
      uploadMedia(sizedFile("avatar.png", "image/png", 2_048), "AVATAR"),
    ).rejects.toThrow(/không khớp/i);
    expect(completeSpy).not.toHaveBeenCalled();
  });

  it("only returns assets that reached ACTIVE status", async () => {
    vi.spyOn(mediaApi, "createUploadSignature").mockResolvedValue(
      authorization,
    );
    vi.spyOn(mediaApi, "completeUpload").mockResolvedValue({
      ...activeAsset,
      status: "PENDING",
    });

    await expect(
      uploadMedia(sizedFile("avatar.png", "image/png", 2_048), "AVATAR"),
    ).rejects.toThrow(/xác minh/i);
  });
});
