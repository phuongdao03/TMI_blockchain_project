import Link from "next/link";

import {
  AccessGuide,
  ProcessGuide,
} from "@/components/public/platform-guidance";
import { isPreviewRelease } from "@/lib/release-mode";

const publicJourney = [
  {
    number: "01",
    title: "Khám phá đề cử",
    detail:
      "Tìm hiểu những con người, tác phẩm và giá trị Việt đã được giới thiệu công khai.",
  },
  {
    number: "02",
    title: "Tìm hiểu câu chuyện",
    detail:
      "Xem nội dung, hình ảnh và thông tin nguồn được phép công bố cho từng đề cử.",
  },
  {
    number: "03",
    title: "Theo dõi chương trình",
    detail:
      "Đăng ký tài khoản để lưu hành trình và nhận thông báo khi các hoạt động mới được mở.",
  },
] as const;

export default function ProcessPage() {
  const preview = isPreviewRelease();

  if (preview) {
    return (
      <div className="process-page">
        <header className="border-b border-neutral-200">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8 lg:py-24">
            <p className="text-xs font-semibold tracking-[0.18em] text-primary-700 uppercase">
              Cách chương trình hoạt động
            </p>
            <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-6xl">
              Hành trình từ một đề cử đến giá trị được lan tỏa.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-neutral-700 sm:text-lg">
              Hiện tại, chương trình tập trung giúp cộng đồng khám phá nội dung
              đã được công bố. Những hoạt động cần gửi thông tin sẽ được mở theo
              từng giai đoạn.
            </p>
          </div>
        </header>

        <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8">
          <ol className="divide-y divide-neutral-200 border-y border-neutral-200">
            {publicJourney.map((step) => (
              <li
                className="grid gap-3 py-8 sm:grid-cols-[4rem_15rem_1fr] sm:items-start"
                key={step.number}
              >
                <span className="font-mono text-sm font-bold text-primary-700">
                  {step.number}
                </span>
                <h2 className="text-xl font-semibold">{step.title}</h2>
                <p className="max-w-2xl leading-7 text-neutral-700">
                  {step.detail}
                </p>
              </li>
            ))}
          </ol>

          <aside className="mt-12 grid gap-6 border border-neutral-300 bg-white p-6 sm:p-8 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <p className="text-xs font-bold tracking-[0.16em] text-primary-700 uppercase">
                Giai đoạn tiếp theo
              </p>
              <h2 className="mt-2 text-2xl font-semibold">
                Cổng gửi đề cử sắp ra mắt
              </h2>
              <p className="mt-3 max-w-2xl leading-7 text-neutral-700">
                Khi được mở, người tham gia sẽ có thể chuẩn bị thông tin, gửi đề
                cử và theo dõi tiến trình ngay trong tài khoản của mình.
              </p>
            </div>
            <Link
              className="inline-flex min-h-12 items-center justify-center rounded-md bg-primary-600 px-5 text-sm font-bold text-white hover:bg-primary-700"
              href="/coming-soon/submission"
            >
              Xem thông tin mở cổng
            </Link>
          </aside>
        </section>
      </div>
    );
  }

  return (
    <div className="bg-[#fbf7f0]">
      <header className="border-b border-neutral-200 text-neutral-950">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 pt-16 pb-14 sm:px-6 lg:grid-cols-[1fr_18rem] lg:px-8 lg:pt-24 lg:pb-20">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-primary-700 uppercase">
              Hành trình gửi hồ sơ
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              Mỗi bước đều rõ việc cần làm và kết quả nhận được.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-700 sm:text-lg">
              Xem trước việc bạn cần làm, cách TMI xử lý và kết quả nhận được ở
              từng mốc.
            </p>
          </div>
          <div className="self-end border-l-2 border-primary-600 pl-5">
            <p className="text-sm leading-6 text-neutral-600">
              Chưa có tài khoản?
            </p>
            <Link
              className="mt-2 inline-flex min-h-11 items-center font-semibold text-primary-700 underline decoration-2 underline-offset-4"
              href="/register"
            >
              Tạo tài khoản
            </Link>
          </div>
        </div>
      </header>
      <ProcessGuide />
      <AccessGuide />
    </div>
  );
}
