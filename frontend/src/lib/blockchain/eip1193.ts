import {
  connect as wagmiConnect,
  disconnect as wagmiDisconnect,
  getAccount,
  getConnectors,
  switchChain as wagmiSwitchChain,
} from "@wagmi/core";
import { POLYGON_CHAIN_ID, wagmiConfig } from "@/lib/blockchain/wagmi-config";

export type Eip1193Provider = {
  request<T>(args: { method: string; params?: unknown[] }): Promise<T>;
  on?(
    event: "accountsChanged" | "chainChanged" | "disconnect",
    listener: () => void,
  ): void;
  removeListener?(
    event: "accountsChanged" | "chainChanged" | "disconnect",
    listener: () => void,
  ): void;
};

let connectedProvider: Eip1193Provider | undefined;
let connectedConnectorUid: string | undefined;

export type WalletRpcError = Error & { code?: number | string };

function provider(): Eip1193Provider {
  const injected =
    typeof window === "undefined"
      ? undefined
      : (window as Window & { ethereum?: Eip1193Provider }).ethereum;
  if (!injected) {
    throw new Error(
      "Không tìm thấy ví tương thích EIP-1193. Hãy cài MetaMask hoặc mở ví của bạn.",
    );
  }
  return injected;
}

async function activeProvider(): Promise<Eip1193Provider> {
  if (connectedProvider) return connectedProvider;
  const account = getAccount(wagmiConfig);
  if (account.isConnected && account.connector) {
    connectedProvider =
      (await account.connector.getProvider()) as Eip1193Provider;
    connectedConnectorUid = account.connector.uid;
    return connectedProvider;
  }
  return provider();
}

export type WalletOption = { id: string; name: string; icon?: string };

export function walletOptions(): WalletOption[] {
  return getConnectors(wagmiConfig).map((connector) => ({
    id: connector.uid,
    name: connector.name,
    icon: connector.icon,
  }));
}

export async function connectWalletWithConnector(
  connectorId: string,
): Promise<{ address: string; chainId: number }> {
  const connector = getConnectors(wagmiConfig).find(
    (candidate) =>
      candidate.uid === connectorId || candidate.id === connectorId,
  );
  if (!connector) throw new Error("Không tìm thấy nhà cung cấp ví.");
  const result = await wagmiConnect(wagmiConfig, {
    connector,
    chainId: POLYGON_CHAIN_ID,
  });
  connectedProvider = (await connector.getProvider()) as Eip1193Provider;
  connectedConnectorUid = connector.uid;
  return { address: result.accounts[0], chainId: Number(result.chainId) };
}

export async function disconnectWallet(): Promise<void> {
  await wagmiDisconnect(wagmiConfig);
  connectedProvider = undefined;
  connectedConnectorUid = undefined;
}

/** Convert provider-specific errors into stable codes for the UI. */
export function walletErrorCode(error: unknown): string {
  const value = error as { code?: number | string; message?: string };
  const message = value?.message?.toLowerCase() ?? "";
  if (value?.code === 4001 || value?.code === "ACTION_REJECTED")
    return "USER_REJECTED";
  if (value?.code === 4100) return "UNAUTHORIZED";
  if (value?.code === 4900 || message.includes("disconnected"))
    return "DISCONNECTED";
  if (value?.code === 4901) return "CHAIN_UNAVAILABLE";
  if (value?.code === -32002 || message.includes("already pending"))
    return "REQUEST_PENDING";
  if (message.includes("not found") || message.includes("no provider"))
    return "NO_WALLET";
  return "WALLET_ERROR";
}

function textToHex(value: string): string {
  const bytes = new TextEncoder().encode(value);
  return `0x${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

export async function connectWallet(): Promise<{
  address: string;
  chainId: number;
}> {
  const active = provider();
  const accounts = await active.request<string[]>({
    method: "eth_requestAccounts",
  });
  const address = accounts[0];
  if (!address) throw new Error("Ví không trả về địa chỉ tài khoản.");
  const chainId = await active.request<string>({ method: "eth_chainId" });
  return { address, chainId: Number.parseInt(chainId, 16) };
}

export async function currentWallet(): Promise<{
  address: string | null;
  chainId: number;
}> {
  const active = await activeProvider();
  const [accounts, chainId] = await Promise.all([
    active.request<string[]>({ method: "eth_accounts" }),
    active.request<string>({ method: "eth_chainId" }),
  ]);
  return {
    address: accounts[0] ?? null,
    chainId: Number.parseInt(chainId, 16),
  };
}

export async function switchChain(chainId: number): Promise<void> {
  if (connectedConnectorUid && chainId === POLYGON_CHAIN_ID) {
    const connector = getConnectors(wagmiConfig).find(
      (candidate) => candidate.uid === connectedConnectorUid,
    );
    await wagmiSwitchChain(wagmiConfig, {
      connector,
      chainId: POLYGON_CHAIN_ID,
    });
    return;
  }
  await provider().request({
    method: "wallet_switchEthereumChain",
    params: [{ chainId: `0x${chainId.toString(16)}` }],
  });
}

export async function signWalletChallenge(
  message: string,
  walletAddress: string,
): Promise<string> {
  return (await activeProvider()).request<string>({
    method: "personal_sign",
    params: [textToHex(message), walletAddress],
  });
}

export async function sendTransaction(
  transactionRequest: Record<string, string>,
): Promise<string> {
  return (await activeProvider()).request<string>({
    method: "eth_sendTransaction",
    params: [transactionRequest],
  });
}

export function subscribeWalletChanges(onChange: () => void): () => void {
  const active = provider();
  active.on?.("accountsChanged", onChange);
  active.on?.("chainChanged", onChange);
  active.on?.("disconnect", onChange);
  return () => {
    active.removeListener?.("accountsChanged", onChange);
    active.removeListener?.("chainChanged", onChange);
    active.removeListener?.("disconnect", onChange);
  };
}
