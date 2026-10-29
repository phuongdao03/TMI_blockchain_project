import { Suspense } from "react";
import { PromotionAdminWorkspace } from "@/components/promotions/promotion-admin-workspace";

export default async function AdminPromotionsPage({
  params,
}: {
  params: Promise<{ section?: string[] }>;
}) {
  const { section } = await params;
  return (
    <Suspense fallback={<p role="status">Đang tải khu vực khuyến mại…</p>}>
      <PromotionAdminWorkspace section={section} />
    </Suspense>
  );
}
