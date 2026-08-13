import { describe, expect, it } from "vitest";

import {
  MAX_LOCAL_VERIFICATION_BYTES,
  compareLocalFile,
  hashLocalFile,
} from "@/lib/verification/file-hash";

describe("local document verification", () => {
  it("calculates SHA-256 locally and matches a public digest", async () => {
    const file = new File(["hello"], "evidence.txt", { type: "text/plain" });
    const expected =
      "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824";

    await expect(hashLocalFile(file)).resolves.toBe(expected);
    await expect(
      compareLocalFile(file, [expected.toUpperCase()]),
    ).resolves.toEqual({ digest: expected, status: "MATCH" });
  });

  it("reports changed files without uploading bytes", async () => {
    const file = new File(["changed"], "evidence.txt");

    await expect(
      compareLocalFile(file, ["ab".repeat(32)]),
    ).resolves.toMatchObject({ status: "NO_MATCH" });
  });

  it("rejects empty, oversized and missing-reference comparisons", async () => {
    await expect(hashLocalFile(new File([], "empty.pdf"))).rejects.toThrow(
      "empty",
    );
    const oversized = {
      size: MAX_LOCAL_VERIFICATION_BYTES + 1,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    } as Blob;
    await expect(hashLocalFile(oversized)).rejects.toThrow("too large");
    await expect(
      compareLocalFile(new File(["hello"], "file.txt"), []),
    ).resolves.toEqual({ digest: null, status: "NO_PUBLIC_REFERENCE" });
  });
});
