import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { DigitalCertificate } from "@/components/public/digital-certificate";
import type { Verification } from "@/lib/api/types";

const data: Verification = {
  status: "VALID",
  checkedAt: "2026-10-06T00:00:00Z",
  certificateNumber: "THV-2026-TEST",
  assetTitle: "Đồng diễn múa Saravan",
  assetSummary: "Mô tả trên bằng",
  categoryName: "Tài sản trí tuệ số",
  issuedAt: "2026-10-06T00:00:00Z",
  expiresAt: null,
  version: 1,
  network: "polygon",
  contractAddress: null,
  transactionHash: null,
  confirmations: 0,
  confirmedAt: null,
  explorerUrl: null,
  recognizedSubject: "Chưa công bố",
  publicAuthorDisplayName: "Trường Đại học Trà Vinh (TVU)",
};

it("shows only the subject frozen in certificate metadata", () => {
  const { rerender } = render(<DigitalCertificate data={data} />);

  expect(screen.getByText("Chưa công bố")).toBeTruthy();
  expect(screen.getByText("Mô tả trên bằng")).toBeTruthy();
  expect(screen.queryByText("Trường Đại học Trà Vinh (TVU)")).toBeNull();
  rerender(<DigitalCertificate data={{ ...data, isCurrentVersion: false }} />);
  expect(screen.getByText("Phiên bản cũ · đã có bản cập nhật")).toBeTruthy();
});

afterEach(() => vi.unstubAllGlobals());

it("acknowledges clipboard success with the canonical verification URL", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  render(<DigitalCertificate data={data} />);
  fireEvent.click(screen.getByRole("button", { name: "Chia sẻ" }));
  expect(
    await screen.findByText("Đã sao chép liên kết tra cứu."),
  ).toBeDefined();
  expect(writeText).toHaveBeenCalledWith(
    `${window.location.origin}/verify/THV-2026-TEST`,
  );
});

it("offers a selectable link when clipboard permission is denied", async () => {
  vi.stubGlobal("navigator", {
    clipboard: {
      writeText: vi
        .fn()
        .mockRejectedValue(new DOMException("denied", "NotAllowedError")),
    },
  });
  render(<DigitalCertificate data={data} />);
  fireEvent.click(screen.getByRole("button", { name: "Chia sẻ" }));
  expect(
    await screen.findByLabelText("Liên kết tra cứu để sao chép"),
  ).toHaveProperty("value", `${window.location.origin}/verify/THV-2026-TEST`);
});

it("treats cancellation as a normal action and allows another share", async () => {
  const share = vi
    .fn()
    .mockRejectedValueOnce(new DOMException("cancelled", "AbortError"))
    .mockResolvedValueOnce(undefined);
  vi.stubGlobal("navigator", { share });
  render(<DigitalCertificate data={data} />);
  fireEvent.click(screen.getByRole("button", { name: "Chia sẻ" }));
  await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Chia sẻ" })).toHaveProperty(
      "disabled",
      false,
    ),
  );
  expect(screen.queryByRole("alert")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Chia sẻ" }));
  expect(
    await screen.findByText("Đã mở chia sẻ liên kết tra cứu."),
  ).toBeDefined();
});
