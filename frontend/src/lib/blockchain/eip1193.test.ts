import { describe, expect, it } from "vitest";

import { walletErrorCode } from "@/lib/blockchain/eip1193";

describe("walletErrorCode", () => {
  it("classifies common provider errors without exposing raw messages", () => {
    expect(walletErrorCode({ code: 4001 })).toBe("USER_REJECTED");
    expect(walletErrorCode({ code: -32002 })).toBe("REQUEST_PENDING");
    expect(walletErrorCode({ code: 4900 })).toBe("DISCONNECTED");
    expect(walletErrorCode({ code: 4100 })).toBe("UNAUTHORIZED");
  });

  it("classifies missing providers", () => {
    expect(walletErrorCode(new Error("No provider found"))).toBe("NO_WALLET");
  });
});
