import { describe, expect, it } from "vitest";

import { isCertificateNumber } from "@/lib/verification/certificate-route";

describe("isCertificateNumber", () => {
  it("routes public certificate numbers through number verification", () => {
    expect(isCertificateNumber("TMI-2026-7EAEC2D2C99A")).toBe(true);
    expect(isCertificateNumber("THV-2026-000001")).toBe(true);
  });

  it("keeps opaque QR tokens on token verification", () => {
    expect(isCertificateNumber("fV4yY5SjdTqLkPMsx8u2Qh8Y4Jk")).toBe(false);
  });
});
