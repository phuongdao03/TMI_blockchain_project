import { describe, expect, it } from "vitest";

import { displayCnsDossierCode } from "@/lib/brand/identifiers";

describe("displayCnsDossierCode", () => {
  it("uses the CNS label for a legacy dossier code without changing other identifiers", () => {
    expect(displayCnsDossierCode("TMI-2026-472D0DAEDD26")).toBe(
      "CNS-2026-472D0DAEDD26",
    );
    expect(displayCnsDossierCode("CNS-2026-472D0DAEDD26")).toBe(
      "CNS-2026-472D0DAEDD26",
    );
    expect(displayCnsDossierCode("ASSET-001")).toBe("ASSET-001");
  });
});
