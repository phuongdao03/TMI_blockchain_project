import type { ReactNode } from "react";

import { WalletProvider } from "@/components/providers/wallet-provider";

export default function BlockchainLayout({ children }: { children: ReactNode }) {
  return <WalletProvider>{children}</WalletProvider>;
}
