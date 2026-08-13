import {
  ArrowRight,
  Building2,
  FileCheck2,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Link from "next/link";

import { FeaturedAssets } from "@/components/public/featured-assets";
import { CertificateOrbit } from "@/components/visual/certificate-orbit";

const audiences = [
  {
    icon: UserRound,
    title: "Cá nhân sáng tạo",
    detail:
      "Tập hợp tác phẩm và tài liệu chứng minh trong một hồ sơ có tiến độ rõ ràng.",
  },
  {
    icon: Building2,
    title: "Tổ chức sở hữu tài sản",
    detail:
      "Chuẩn hóa thông tin, phối hợp bổ sung tài liệu và nhận kết quả phát hành.",
  },
  {
    icon: Search,
    title: "Người cần kiểm tra",
    detail:
      "Tra cứu chứng thư và đối chiếu thông tin đã được cho phép công bố.",
  },
] as const;

const journey = [
  [
    "01",
    "Thiết lập hồ sơ",
    "Tập hợp thông tin tác phẩm và tài liệu chứng minh.",
  ],
  [
    "02",
    "Theo dõi thẩm định",
    "Nhận trạng thái rõ ràng và bổ sung khi được yêu cầu.",
  ],
  [
    "03",
    "Nhận chứng thư",
    "Tải kết quả và chia sẻ đường dẫn kiểm tra độc lập.",
  ],
] as const;

export default function HomePage() {
  return (
    <div className="overflow-hidden bg-[#070a12] text-white">
      <section
        className="registry-hero relative border-b border-white/10"
        id="gioi-thieu"
      >
        <div className="registry-hero-glow" aria-hidden="true" />
        <div className="mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-[100rem] items-center gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[0.88fr_1.12fr] lg:gap-5 lg:px-8 lg:py-16 xl:px-14">
          <div className="relative z-10 max-w-[44rem] lg:py-8">
            <p className="registry-kicker">
              <span aria-hidden="true" className="registry-kicker-dot" />
              Hệ thống đăng bộ &amp; xác minh
            </p>
            <h1 className="mt-10 text-[clamp(2.9rem,5.5vw,5.65rem)] font-semibold leading-[0.98] tracking-[-0.055em] text-balance">
              Bằng chứng cho giá trị số,{" "}
              <span className="text-[#f3d675]">
                được thiết kế để kiểm chứng.
              </span>
            </h1>
            <p className="mt-8 max-w-[41rem] text-base leading-8 text-slate-300 sm:text-lg">
              TMI tổ chức hồ sơ, thẩm định, chứng thư và dấu vết xác minh thành
              một chuỗi bằng chứng nhất quán — để mỗi giá trị số đều có nguồn
              gốc rõ ràng và có thể đối chiếu độc lập.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                className="registry-button registry-button-primary"
                href="/register"
              >
                Khởi tạo hồ sơ{" "}
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
              <Link
                className="registry-button registry-button-secondary"
                href="/process"
              >
                Khám phá quy trình
              </Link>
            </div>
            <form
              action="/search"
              aria-label="Tra cứu tài sản hoặc chứng thư"
              className="registry-search mt-6"
              role="search"
            >
              <Search
                aria-hidden="true"
                className="size-5 shrink-0 text-slate-500"
              />
              <label className="sr-only" htmlFor="registry-search-input">
                Tra cứu tài sản hoặc số chứng thư
              </label>
              <input
                id="registry-search-input"
                name="query"
                placeholder="Tra cứu tài sản hoặc số chứng thư"
              />
              <button type="submit">Tra cứu</button>
            </form>
            <dl className="mt-8 grid grid-cols-3 border-t border-white/15 pt-6 text-sm">
              {[
                ["Dữ liệu", "Bảo toàn"],
                ["Trạng thái", "Minh bạch"],
                ["Xác minh", "Độc lập"],
              ].map(([term, detail]) => (
                <div
                  className="border-l border-white/20 px-4 first:border-l-0 first:pl-0"
                  key={term}
                >
                  <dt className="text-xs text-slate-500">{term}</dt>
                  <dd className="mt-1 font-semibold text-slate-200">
                    {detail}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="registry-visual relative min-w-0 self-stretch lg:-mr-14">
            <CertificateOrbit />
          </div>
        </div>
      </section>

      <section className="border-b border-white/10 bg-[#0c1220]">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[0.72fr_1.28fr] lg:gap-20 lg:px-8 lg:py-28">
          <div>
            <p className="registry-section-label">Một hành trình rõ ràng</p>
            <h2 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-5xl">
              Mỗi bước đều tạo ra một kết quả có thể theo dõi.
            </h2>
            <p className="mt-6 max-w-lg leading-7 text-slate-400">
              Bạn luôn biết việc cần làm tiếp theo mà không phải đọc thuật ngữ
              kỹ thuật hoặc cấu trúc vận hành nội bộ.
            </p>
          </div>
          <ol className="border-t border-white/15">
            {journey.map(([number, title, detail]) => (
              <li
                className="group grid gap-4 border-b border-white/15 py-7 sm:grid-cols-[4rem_1fr_auto] sm:items-center"
                key={number}
              >
                <span className="font-mono text-xs text-[#ff5545]">
                  {number}
                </span>
                <div>
                  <h3 className="text-xl font-semibold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {detail}
                  </p>
                </div>
                <ArrowRight
                  aria-hidden="true"
                  className="hidden size-5 text-[#f3d675] transition-transform group-hover:translate-x-1 sm:block"
                />
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="bg-[#f2efe7] text-[#172033]">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
            Bắt đầu theo nhu cầu
          </p>
          <div className="mt-5 flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-5xl">
              Một nền tảng, ba cách sử dụng rõ ràng.
            </h2>
            <Link
              className="inline-flex items-center gap-2 text-sm font-bold text-primary-700"
              href="/process"
            >
              Xem quy trình <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </div>
          <div className="mt-14 grid border-y border-slate-300 md:grid-cols-3 md:divide-x md:divide-slate-300">
            {audiences.map(({ detail, icon: Icon, title }) => (
              <article
                className="py-9 md:px-8 md:first:pl-0 md:last:pr-0"
                key={title}
              >
                <Icon
                  aria-hidden="true"
                  className="size-6 text-primary-700"
                  strokeWidth={1.6}
                />
                <h3 className="mt-8 text-xl font-semibold">{title}</h3>
                <p className="mt-3 max-w-sm text-sm leading-6 text-slate-600">
                  {detail}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 bg-[#0e0e0e]">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-24">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <p className="registry-section-label">Tác phẩm đã công bố</p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
                Kiểm tra những kết quả đã phát hành.
              </h2>
            </div>
            <Link className="text-sm font-bold text-[#f3d675]" href="/works">
              Xem thư viện{" "}
              <ArrowRight aria-hidden="true" className="ml-1 inline size-4" />
            </Link>
          </div>
          <div className="mt-10 text-slate-900">
            <FeaturedAssets />
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 bg-[#0e0e0e]">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-16 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div className="max-w-2xl">
            <ShieldCheck aria-hidden="true" className="size-6 text-[#f3d675]" />
            <h2 className="mt-5 text-3xl font-semibold tracking-tight">
              Sẵn sàng tạo hồ sơ đầu tiên?
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Lưu bản nháp và quay lại hoàn thiện khi bạn đã chuẩn bị đủ tài
              liệu.
            </p>
          </div>
          <Link
            className="registry-button registry-button-primary"
            href="/register"
          >
            Khởi tạo hồ sơ <FileCheck2 aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
