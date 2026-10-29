import { VoucherDetail } from "@/components/vouchers/voucher-detail";
export default async function VoucherDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <VoucherDetail id={id} />;
}
