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

declare global {
  interface Window {
    ethereum?: Eip1193Provider;
  }
}

function provider(): Eip1193Provider {
  if (typeof window === "undefined" || !window.ethereum) {
    throw new Error(
      "Không tìm thấy ví tương thích EIP-1193. Hãy cài MetaMask hoặc mở ví của bạn.",
    );
  }
  return window.ethereum;
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
  const active = provider();
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
  await provider().request({
    method: "wallet_switchEthereumChain",
    params: [{ chainId: `0x${chainId.toString(16)}` }],
  });
}

export async function signWalletChallenge(
  message: string,
  walletAddress: string,
): Promise<string> {
  return provider().request<string>({
    method: "personal_sign",
    params: [textToHex(message), walletAddress],
  });
}

export async function sendTransaction(
  transactionRequest: Record<string, string>,
): Promise<string> {
  return provider().request<string>({
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
