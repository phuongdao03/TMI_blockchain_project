import {
  ArrowRight,
  BookOpenText,
  CircleUserRound,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { ApplicantUpgradeCard } from "@/components/dashboard/applicant-upgrade-card";

export function PreviewDashboard() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="max-w-3xl">
        <p className="font-mono text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary-700">
          Không gian của bạn
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">
          Khám phá những đề cử đang được giới thiệu
        </h1>
        <p className="mt-4 text-base leading-7 text-neutral-600">
          Theo dõi các nội dung đã công bố, cập nhật thông tin cá nhân và tìm
          hiểu cách tham gia khi cổng đề cử chính thức mở.
        </p>
      </header>

      <ApplicantUpgradeCard preview />

      <section className="hero-grid-surface overflow-hidden rounded-2xl border border-white/8 bg-[#151515] px-6 py-8 text-white sm:px-9 sm:py-10 lg:grid lg:grid-cols-[1fr_auto] lg:items-end lg:gap-12">
        <div className="max-w-2xl">
          <span className="grid size-11 place-items-center rounded-lg border border-gold-300/30 bg-gold-300/10 text-gold-300">
            <Sparkles aria-hidden="true" className="size-5" />
          </span>
          <h2 className="mt-7 text-2xl font-bold tracking-[-0.03em] sm:text-3xl">
            Những câu chuyện đáng chú ý
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Khám phá tác phẩm, con người và những giá trị Việt đang được giới
            thiệu tới cộng đồng.
          </p>
        </div>
        <Link
          className="mt-7 inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-bold text-white hover:bg-primary-500 lg:mt-0"
          href="/works"
        >
          Xem thư viện <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </section>

      <section className="grid overflow-hidden rounded-xl border border-black/10 bg-[#fbfaf7] md:grid-cols-2">
        <Link
          className="group border-b border-black/8 p-6 transition-colors hover:bg-white md:border-r md:border-b-0"
          href="/account"
        >
          <CircleUserRound className="size-6 text-primary-700" />
          <h2 className="mt-5 text-lg font-bold">Hoàn thiện tài khoản</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Cập nhật tên hiển thị và thông tin liên hệ của bạn.
          </p>
        </Link>
        <Link
          className="group p-6 transition-colors hover:bg-white"
          href="/process"
        >
          <BookOpenText className="size-6 text-primary-700" />
          <h2 className="mt-5 text-lg font-bold">Xem hành trình dự kiến</h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Xem các mốc dự kiến từ chuẩn bị đề cử đến khi công bố kết quả.
          </p>
        </Link>
      </section>
    </div>
  );
}
