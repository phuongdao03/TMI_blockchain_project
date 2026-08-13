import Link from "next/link";

import {
  AccessGuide,
  ProcessGuide,
} from "@/components/public/platform-guidance";

export default function ProcessPage() {
  return (
    <div className="bg-[#fbf7f0]">
      <header className="border-b border-neutral-200 text-neutral-950">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 pt-16 pb-14 sm:px-6 lg:grid-cols-[1fr_18rem] lg:px-8 lg:pt-24 lg:pb-20">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-primary-700 uppercase">
              Hướng dẫn hồ sơ
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              Từ chuẩn bị tài liệu đến nhận chứng thư.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-700 sm:text-lg">
              Xem trước việc bạn cần làm, cách TMI xử lý và kết quả nhận được ở
              từng mốc.
            </p>
          </div>
          <div className="self-end border-l-2 border-primary-600 pl-5">
            <p className="text-sm leading-6 text-neutral-600">
              Đã sẵn sàng gửi tác phẩm?
            </p>
            <Link
              className="mt-2 inline-flex min-h-11 items-center font-semibold text-primary-700 underline decoration-2 underline-offset-4"
              href="/register"
            >
              Bắt đầu hồ sơ
            </Link>
          </div>
        </div>
      </header>
      <ProcessGuide />
      <AccessGuide />
    </div>
  );
}
