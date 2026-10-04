import { describe, expect, it } from "vitest";

import { displayCnsDossierCode } from "@/lib/brand/identifiers";

describe("displayCnsDossierCode", () => {
  it("hides old brand codes without changing current identifiers", () => {
    expect(displayCnsDossierCode("TMI-2026-472D0DAEDD26")).toBe(
      "Hồ sơ lưu trữ",
    );
    expect(displayCnsDossierCode("CNS-2026-472D0DAEDD26")).toBe(
      "Hồ sơ lưu trữ",
    );
    expect(displayCnsDossierCode("THV-2026-001")).toBe("THV-2026-001");
  });
});
