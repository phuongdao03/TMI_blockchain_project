import { describe, expect, it } from "vitest";

import { formatVndInput, parseVndInput } from "./format-vnd-input";

describe("salary input", () => {
  it("formats VND while preserving the unformatted API value", () => {
    expect(formatVndInput("7000000")).toBe("7.000.000");
    expect(parseVndInput("7.000.000")).toBe("7000000");
    expect(formatVndInput("7.000.000đ")).toBe("7.000.000");
  });
});
