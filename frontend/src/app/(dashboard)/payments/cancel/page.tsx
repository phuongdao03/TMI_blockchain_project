import { PaymentReturnWorkspace } from "@/components/payments/payment-return-workspace";

export default async function PaymentCancelPage({
  searchParams,
}: {
  searchParams: Promise<{ id?: string }>;
}) {
  const { id } = await searchParams;
  return <PaymentReturnWorkspace providerOrderId={id} />;
}
