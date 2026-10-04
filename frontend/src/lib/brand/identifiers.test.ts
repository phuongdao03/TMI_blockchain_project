import { describe, expect, it } from "vitest";

import { displayCnsDossierCode } from "@/lib/brand/identifiers";

describe("displayCnsDossierCode", () => {
  it("shows a stable THV display code for legacy dossiers", () => {
    expect(displayCnsDossierCode("TMI-2026-472D0DAEDD26")).toBe(
      "THV-2026-472D0DAEDD26",
    );
    expect(displayCnsDossierCode("CNS-2026-472D0DAEDD26")).toBe(
      "THV-2026-472D0DAEDD26",
    );
    expect(displayCnsDossierCode("THV-2026-001")).toBe("THV-2026-001");
  });
});
