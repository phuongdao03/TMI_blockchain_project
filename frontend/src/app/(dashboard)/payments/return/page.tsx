import { PaymentReturnWorkspace } from "@/components/payments/payment-return-workspace";
import { WalletWorkspace } from "@/components/wallet/wallet-workspace";

export default async function PaymentReturnPage({
  searchParams,
}: {
  searchParams: Promise<{ id?: string; orderCode?: string }>;
}) {
  const { id, orderCode } = await searchParams;
  if (
    orderCode &&
    /^\d{1,16}$/.test(orderCode) &&
    Number(orderCode) > 2_147_483_647
  )
    return <WalletWorkspace />;
  return <PaymentReturnWorkspace providerOrderId={id} />;
}
