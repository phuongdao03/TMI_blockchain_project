import { PaymentWorkspace } from "@/components/payments/payment-workspace";

export default async function PaymentPage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = await params;
  return <PaymentWorkspace orderId={orderId} />;
}
