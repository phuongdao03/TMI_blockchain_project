import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FileUploader } from "@/components/media/file-uploader";
import type { MediaAsset } from "@/lib/api/types";

const uploadMediaMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/media/upload", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/media/upload")>();
  return {
    ...actual,
    uploadMedia: uploadMediaMock,
  };
});

const activeAsset: MediaAsset = {
  id: "6a0bb388-3c26-4417-aed8-3ca05c212d1f",
  status: "ACTIVE",
  mimeType: "image/png",
  bytes: 2_048,
  width: 512,
  height: 512,
  durationMs: null,
};

describe("FileUploader", () => {
  beforeEach(() => {
    uploadMediaMock.mockReset();
  });

  it("announces progress and returns the verified media asset", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    let finishUpload: ((asset: MediaAsset) => void) | undefined;
    uploadMediaMock.mockImplementation(
      async (
        _file: File,
        _purpose: string,
        callbacks: {
          onProgress: (progress: number) => void;
          onStage: (stage: string) => void;
        },
      ) => {
        callbacks.onStage("uploading");
        callbacks.onProgress(64);
        return new Promise<MediaAsset>((resolve) => {
          finishUpload = resolve;
        });
      },
    );
    render(
      <FileUploader
        label="Ảnh đại diện"
        onComplete={onComplete}
        purpose="AVATAR"
      />,
    );

    const file = new File(["avatar"], "avatar.png", { type: "image/png" });
    await user.upload(screen.getByLabelText("Chọn ảnh đại diện"), file);
    expect(screen.getByText("avatar.png")).toBeDefined();
    expect(screen.getByRole("status").textContent).toContain(
      "Sẵn sàng tải lên",
    );

    await user.click(screen.getByRole("button", { name: "Tải lên" }));
    expect(screen.getByRole("progressbar").getAttribute("value")).toBe("64");
    expect(screen.getByRole("status").textContent).toContain(
      "Đang tải lên Cloudinary · 64%",
    );

    finishUpload?.(activeAsset);
    await vi.waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain(
        "Tệp đã được tải lên và xác minh.",
      );
    });
    expect(onComplete).toHaveBeenCalledWith(activeAsset);
  });

  it("keeps the selected file and retries with a fresh upload attempt", async () => {
    const user = userEvent.setup();
    uploadMediaMock
      .mockRejectedValueOnce(new Error("Mạng không ổn định."))
      .mockResolvedValueOnce(activeAsset);
    render(
      <FileUploader
        label="Ảnh đại diện"
        onComplete={vi.fn()}
        purpose="AVATAR"
      />,
    );

    await user.upload(
      screen.getByLabelText("Chọn ảnh đại diện"),
      new File(["avatar"], "avatar.png", { type: "image/png" }),
    );
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Mạng không ổn định.",
    );
    await user.click(screen.getByRole("button", { name: "Thử lại" }));

    await vi.waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain(
        "Tệp đã được tải lên và xác minh.",
      );
    });
    expect(uploadMediaMock).toHaveBeenCalledTimes(2);
    expect(uploadMediaMock.mock.calls[0]?.[0]).toBe(
      uploadMediaMock.mock.calls[1]?.[0],
    );
  });

  it("rejects an invalid selected file before starting an upload", () => {
    render(
      <FileUploader
        label="Ảnh đại diện"
        onComplete={vi.fn()}
        purpose="AVATAR"
      />,
    );

    fireEvent.change(screen.getByLabelText("Chọn ảnh đại diện"), {
      target: {
        files: [
          new File(["document"], "document.pdf", {
            type: "application/pdf",
          }),
        ],
      },
    });

    expect(screen.getByRole("alert").textContent).toContain(
      "Định dạng tệp không được hỗ trợ",
    );
    expect(uploadMediaMock).not.toHaveBeenCalled();
  });

  it("accepts a valid file dropped onto the upload zone", () => {
    render(
      <FileUploader
        label="Bằng chứng hồ sơ"
        onComplete={vi.fn()}
        purpose="DOSSIER_EVIDENCE"
      />,
    );
    const file = new File(["document"], "evidence.pdf", {
      type: "application/pdf",
    });

    fireEvent.drop(
      screen.getByRole("group", { name: "Vùng tải bằng chứng hồ sơ" }),
      {
        dataTransfer: { files: [file] },
      },
    );

    expect(screen.getByText("evidence.pdf")).toBeDefined();
    expect(screen.getByRole("button", { name: "Tải lên" })).toBeDefined();
  });
});
