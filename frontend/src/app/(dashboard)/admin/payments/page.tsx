import { PaymentRequestWorkspace } from "@/components/admin/payment-request-workspace";

export default async function AdminPaymentsPage({
  searchParams,
}: PageProps<"/admin/payments">) {
  const { dossierId } = await searchParams;
  return (
    <PaymentRequestWorkspace
      initialDossierId={typeof dossierId === "string" ? dossierId : undefined}
    />
  );
}
