import { WalletWorkspace } from "@/components/wallet/wallet-workspace";

export default async function WalletPage({
  searchParams,
}: {
  searchParams: Promise<{ returnTo?: string }>;
}) {
  const { returnTo } = await searchParams;
  return <WalletWorkspace returnTo={returnTo} />;
}
