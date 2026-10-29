"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { voucherApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { VoucherCard } from "./voucher-card";

export function VoucherDetail({ id }: { id: string }) {
  const user = useAuthUser();
  const voucher = useQuery({
    queryKey: ["vouchers", "detail", user?.id, id],
    queryFn: () => voucherApi.detail(id),
    enabled: Boolean(user),
  });
  return (
    <section className="mx-auto max-w-3xl space-y-5">
      <Link
        className="text-sm font-semibold text-[var(--theme-text)]"
        href="/vouchers"
      >
        ← Voucher của tôi
      </Link>
      {voucher.isPending && <p role="status">Đang tải ưu đãi…</p>}
      {voucher.isError && (
        <p role="alert">
          Không tìm thấy ưu đãi hoặc bạn không có quyền truy cập.
        </p>
      )}
      {voucher.data && <VoucherCard voucher={voucher.data} detail />}
    </section>
  );
}
