import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
  getAccount: vi.fn(),
  getConnectors: vi.fn(),
  switchChain: vi.fn(),
}));

vi.mock("@wagmi/core", () => ({
  connect: mocks.connect,
  disconnect: mocks.disconnect,
  getAccount: mocks.getAccount,
  getConnectors: mocks.getConnectors,
  switchChain: mocks.switchChain,
}));
vi.mock("@/lib/blockchain/wagmi-config", () => ({
  POLYGON_CHAIN_ID: 137,
  wagmiConfig: { id: "test-config" },
}));

import {
  connectWalletWithConnector,
  subscribeWalletChanges,
  walletAddressesMatch,
  walletErrorCode,
} from "@/lib/blockchain/eip1193";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getAccount.mockReturnValue({ isConnected: false });
  mocks.getConnectors.mockReturnValue([]);
});

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

  it("compares authorized addresses without checksum casing", () => {
    expect(
      walletAddressesMatch(
        "0xBfA38182f0D24589e7898DD4892C58c3FDa58042",
        "0xbfa38182f0d24589e7898dd4892c58c3fda58042",
      ),
    ).toBe(true);
  });

  it("subscribes to the active connector provider for mobile wallets", async () => {
    const provider = {
      request: vi.fn(),
      on: vi.fn(),
      removeListener: vi.fn(),
    };
    const connector = {
      uid: "wallet-connect-1",
      id: "walletConnect",
      name: "WalletConnect",
      getProvider: vi.fn(async () => provider),
    };
    mocks.getConnectors.mockReturnValue([connector]);
    mocks.connect.mockResolvedValue({
      accounts: ["0xbfa38182f0d24589e7898dd4892c58c3fda58042"],
      chainId: 137,
    });

    await connectWalletWithConnector(connector.uid);
    const unsubscribe = subscribeWalletChanges(vi.fn());
    await Promise.resolve();

    expect(provider.on).toHaveBeenCalledTimes(3);
    unsubscribe();
    expect(provider.removeListener).toHaveBeenCalledTimes(3);
  });
});
