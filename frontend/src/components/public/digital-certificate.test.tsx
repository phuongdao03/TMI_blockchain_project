import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { DigitalCertificate } from "@/components/public/digital-certificate";
import type { Verification } from "@/lib/api/types";

it("shows only the subject frozen in certificate metadata", () => {
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

  const { rerender } = render(<DigitalCertificate data={data} />);

  expect(screen.getByText("Chưa công bố")).toBeTruthy();
  expect(screen.getByText("Mô tả trên bằng")).toBeTruthy();
  expect(screen.queryByText("Trường Đại học Trà Vinh (TVU)")).toBeNull();
  rerender(<DigitalCertificate data={{ ...data, isCurrentVersion: false }} />);
  expect(screen.getByText("Phiên bản cũ · đã có bản cập nhật")).toBeTruthy();
});
