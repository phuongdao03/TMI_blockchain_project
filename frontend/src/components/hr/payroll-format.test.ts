import { describe, expect, it } from "vitest";

import { formatVnd } from "@/components/hr/payroll-format";

describe("formatVnd", () => {
  it("preserves every digit of large VND values returned as decimal strings", () => {
    expect(formatVnd("999999999999999999")).toBe("999.999.999.999.999.999 ₫");
  });
});
