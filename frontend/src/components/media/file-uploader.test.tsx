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

  it("explains the upload policy before a file is selected", () => {
    render(
      <FileUploader
        label="Bằng chứng hồ sơ"
        onComplete={vi.fn()}
        purpose="DOSSIER_EVIDENCE"
      />,
    );

    expect(screen.getByText(/Mỗi tệp tối đa 100 MB/)).toBeDefined();
    expect(screen.getByText(/kiểm tra an toàn/)).toBeDefined();
    expect(screen.getByRole("button", { name: "Thêm tệp" })).toBeDefined();
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

    await user.click(screen.getByRole("button", { name: "Tải lên 1 tệp" }));
    expect(screen.getByRole("progressbar").getAttribute("value")).toBe("64");
    expect(screen.getByRole("button", { name: "Đang xử lý" })).toBeDefined();
    expect(screen.getByRole("status").textContent).toContain(
      "Đang tải tệp · 64%",
    );
    expect(screen.queryByText(/Cloudinary/i)).toBeNull();

    finishUpload?.(activeAsset);
    await vi.waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain(
        "Tệp đã được tải lên và xác minh.",
      );
    });
    expect(onComplete).toHaveBeenCalledWith(activeAsset, 0);
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
    await user.click(screen.getByRole("button", { name: "Tải lên 1 tệp" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Mạng không ổn định.",
    );
    await user.click(screen.getByRole("button", { name: "Thử lại 1 tệp" }));

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
    expect(screen.getByRole("button", { name: "Tải lên 1 tệp" })).toBeDefined();
  });

  it("uses the selected dossier rule for the picker and browser validation", () => {
    render(
      <FileUploader
        constraints={{
          allowedMimeTypes: ["application/pdf"],
          maxBytes: 1_048_576,
        }}
        label="Giấy tờ quyền sở hữu"
        onComplete={vi.fn()}
        purpose="DOSSIER_EVIDENCE"
      />,
    );

    const input = screen.getByLabelText("Chọn giấy tờ quyền sở hữu");
    expect(input.getAttribute("accept")).toBe("application/pdf");
    fireEvent.change(input, {
      target: {
        files: [new File(["image"], "ownership.png", { type: "image/png" })],
      },
    });

    expect(screen.getByRole("alert").textContent).toContain(
      "Định dạng tệp không phù hợp",
    );
  });

  it("uploads a selected dossier evidence batch in order", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    const secondAsset = { ...activeAsset, id: "asset-2" };
    uploadMediaMock
      .mockResolvedValueOnce(activeAsset)
      .mockResolvedValueOnce(secondAsset);

    render(
      <FileUploader
        label="Bằng chứng hồ sơ"
        multiple
        onComplete={onComplete}
        purpose="DOSSIER_EVIDENCE"
      />,
    );

    const files = [
      new File(["one"], "one.pdf", { type: "application/pdf" }),
      new File(["two"], "two.pdf", { type: "application/pdf" }),
    ];
    await user.upload(screen.getByLabelText("Chọn bằng chứng hồ sơ"), files);

    expect(screen.getByText("one.pdf")).toBeDefined();
    expect(screen.getByText("two.pdf")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Tải lên 2 tệp" }));

    await vi.waitFor(() => expect(uploadMediaMock).toHaveBeenCalledTimes(2));
    expect(uploadMediaMock.mock.calls[0]?.[0]).toBe(files[0]);
    expect(uploadMediaMock.mock.calls[1]?.[0]).toBe(files[1]);
    expect(onComplete).toHaveBeenNthCalledWith(1, activeAsset, 0);
    expect(onComplete).toHaveBeenNthCalledWith(2, secondAsset, 1);
  });

  it("rejects a batch larger than the remaining evidence capacity", async () => {
    const user = userEvent.setup();
    render(
      <FileUploader
        label="Báº±ng chá»©ng há»“ sÆ¡"
        maxFiles={1}
        multiple
        onComplete={vi.fn()}
        purpose="DOSSIER_EVIDENCE"
      />,
    );

    const input = document.querySelector('input[type="file"]');
    expect(input).not.toBeNull();
    await user.upload(input as HTMLInputElement, [
      new File(["one"], "one.pdf", { type: "application/pdf" }),
      new File(["two"], "two.pdf", { type: "application/pdf" }),
    ]);

    expect(screen.getByRole("alert").textContent).toContain("1");
    expect(uploadMediaMock).not.toHaveBeenCalled();
  });

  it("appends files selected in separate batches and lets the user remove one", async () => {
    const user = userEvent.setup();
    render(
      <FileUploader
        label="Bằng chứng hồ sơ"
        maxFiles={4}
        multiple
        onComplete={vi.fn()}
        purpose="DOSSIER_EVIDENCE"
      />,
    );

    const input = screen.getByLabelText("Chọn bằng chứng hồ sơ");
    await user.upload(
      input,
      new File(["one"], "one.pdf", { type: "application/pdf" }),
    );
    await user.upload(
      input,
      new File(["two"], "two.pdf", { type: "application/pdf" }),
    );

    expect(screen.getByText("one.pdf")).toBeDefined();
    expect(screen.getByText("two.pdf")).toBeDefined();
    expect(screen.getByRole("button", { name: "Thêm tệp" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Tải lên 2 tệp" })).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Xóa one.pdf" }));
    expect(screen.queryByText("one.pdf")).toBeNull();
    expect(screen.getByText("two.pdf")).toBeDefined();
  });

  it("continues after one file fails and retries only that file", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    const secondAsset = { ...activeAsset, id: "asset-2" };
    uploadMediaMock
      .mockRejectedValueOnce(new Error("Kết nối bị gián đoạn."))
      .mockResolvedValueOnce(secondAsset)
      .mockResolvedValueOnce(activeAsset);
    render(
      <FileUploader
        label="Bằng chứng hồ sơ"
        multiple
        onComplete={onComplete}
        purpose="DOSSIER_EVIDENCE"
      />,
    );

    const files = [
      new File(["one"], "one.pdf", { type: "application/pdf" }),
      new File(["two"], "two.pdf", { type: "application/pdf" }),
    ];
    await user.upload(screen.getByLabelText("Chọn bằng chứng hồ sơ"), files);
    await user.click(screen.getByRole("button", { name: "Tải lên 2 tệp" }));

    await vi.waitFor(() => expect(uploadMediaMock).toHaveBeenCalledTimes(2));
    expect(onComplete).toHaveBeenCalledWith(secondAsset, 0);
    expect(screen.getByText("Kết nối bị gián đoạn.")).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Thử lại 1 tệp" }));
    await vi.waitFor(() => expect(uploadMediaMock).toHaveBeenCalledTimes(3));
    expect(uploadMediaMock.mock.calls[2]?.[0]).toBe(files[0]);
    expect(onComplete).toHaveBeenCalledTimes(2);
  });
});
