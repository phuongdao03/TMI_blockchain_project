import {
  ArrowRight,
  Landmark,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import Link from "next/link";

import { FeaturedAssets } from "@/components/public/featured-assets";
import { CertificateOrbit } from "@/components/visual/certificate-orbit";
import { isPreviewRelease } from "@/lib/release-mode";

const audiences = [
  {
    icon: Landmark,
    title: "Di sản & văn hóa",
    detail:
      "Những giá trị được gìn giữ, trao truyền và tiếp tục sống trong đời sống hôm nay.",
  },
  {
    icon: Sparkles,
    title: "Sáng tạo Việt",
    detail:
      "Tác phẩm, sản phẩm và ý tưởng thể hiện bản sắc cùng năng lực sáng tạo đương đại.",
  },
  {
    icon: UserRound,
    title: "Con người & cộng đồng",
    detail:
      "Những cá nhân, tập thể và sáng kiến tạo nên ảnh hưởng tích cực, bền vững.",
  },
] as const;

const journey = [
  [
    "01",
    "Khám phá đề cử",
    "Xem những gương mặt, tác phẩm và giá trị Việt đang được giới thiệu.",
  ],
  [
    "02",
    "Hiểu câu chuyện",
    "Tìm hiểu bối cảnh, dấu ấn và những thông tin đã được công bố.",
  ],
  [
    "03",
    "Kiểm tra minh bạch",
    "Đối chiếu trạng thái và bằng chứng khi một đề cử có dữ liệu xác thực.",
  ],
] as const;

export default function HomePage() {
  const preview = isPreviewRelease();
  return (
    <div className="public-home overflow-hidden">
      <section
        className="registry-hero relative border-b border-white/10"
        id="gioi-thieu"
      >
        <div className="registry-hero-glow" aria-hidden="true" />
        <div className="mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-[100rem] items-center gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[0.88fr_1.12fr] lg:gap-5 lg:px-8 lg:py-16 xl:px-14">
          <div className="relative z-10 max-w-[44rem] lg:py-8">
            <p className="registry-kicker">
              <span aria-hidden="true" className="registry-kicker-dot" />
              Đề cử Tinh Hoa Việt
            </p>
            <h1 className="mt-10 text-[clamp(2.9rem,5.5vw,5.65rem)] font-semibold leading-[0.98] tracking-[-0.055em] text-balance">
              Nơi những giá trị Việt được giới thiệu,{" "}
              <span className="text-[#f3d675]">ghi nhận và lan tỏa.</span>
            </h1>
            <p className="mt-8 max-w-[41rem] text-base leading-8 text-slate-300 sm:text-lg">
              Khám phá các đề cử tiêu biểu, đọc câu chuyện phía sau mỗi giá trị
              và theo dõi thông tin được công bố minh bạch. Bình chọn và cổng
              gửi đề cử sẽ được mở ở giai đoạn tiếp theo.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                className="registry-button registry-button-primary"
                href="/works"
              >
                Khám phá đề cử{" "}
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
              <Link
                className="registry-button registry-button-secondary"
                href="/process"
              >
                Tìm hiểu chương trình
              </Link>
            </div>
            <form
              action="/works"
              aria-label="Tìm kiếm đề cử"
              className="registry-search mt-6"
              role="search"
            >
              <Search
                aria-hidden="true"
                className="size-5 shrink-0 text-slate-500"
              />
              <label className="sr-only" htmlFor="registry-search-input">
                Tìm theo tên, câu chuyện hoặc lĩnh vực
              </label>
              <input
                id="registry-search-input"
                name="query"
                placeholder="Tìm kiếm đề cử"
              />
              <button type="submit">Tra cứu</button>
            </form>
            <dl className="mt-8 grid grid-cols-3 border-t border-white/15 pt-6 text-sm">
              {[
                ["Nội dung", "Chọn lọc"],
                ["Thông tin", "Rõ ràng"],
                ["Dữ liệu", "Kiểm chứng"],
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
            <CertificateOrbit preview={preview} />
          </div>
        </div>
      </section>

      <section className="home-journey border-b">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[0.72fr_1.28fr] lg:gap-20 lg:px-8 lg:py-28">
          <div>
            <p className="registry-section-label">
              Khám phá theo cách tự nhiên
            </p>
            <h2 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-5xl">
              Bắt đầu từ câu chuyện, đi sâu vào thông tin minh bạch.
            </h2>
            <p className="mt-6 max-w-lg leading-7 text-slate-400">
              Hiện tại, bạn có thể xem và tìm hiểu những nội dung đã được công
              bố. Các hoạt động tham gia sẽ mở khi quy trình đã sẵn sàng.
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

      <section className="home-audiences">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
            Những giá trị đang được giới thiệu
          </p>
          <div className="mt-5 flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-5xl">
              Đa dạng lĩnh vực, cùng chung một niềm tự hào Việt.
            </h2>
            <Link
              className="inline-flex items-center gap-2 text-sm font-bold text-primary-700"
              href="/works"
            >
              Xem tất cả đề cử{" "}
              <ArrowRight aria-hidden="true" className="size-4" />
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

      <section className="home-featured border-t">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-24">
          <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <p className="registry-section-label">
                {preview ? "Những đề cử đầu tiên" : "Đề cử đã công bố"}
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
                {preview
                  ? "Khám phá những câu chuyện mở đầu."
                  : "Khám phá những giá trị đang được lan tỏa."}
              </h2>
            </div>
            <Link className="text-sm font-bold text-[#f3d675]" href="/works">
              Xem các đề cử{" "}
              <ArrowRight aria-hidden="true" className="ml-1 inline size-4" />
            </Link>
          </div>
          <div className="mt-10 text-slate-900">
            <FeaturedAssets />
          </div>
        </div>
      </section>

      <section className="home-cta border-t">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-16 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div className="max-w-2xl">
            <ShieldCheck aria-hidden="true" className="size-6 text-[#f3d675]" />
            <h2 className="mt-5 text-3xl font-semibold tracking-tight">
              {preview
                ? "Muốn theo dõi hành trình Tinh Hoa Việt?"
                : "Tiếp tục khám phá Tinh Hoa Việt"}
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              {preview
                ? "Tạo tài khoản để sử dụng các tiện ích cá nhân và nhận thông tin khi những hoạt động mới được mở."
                : "Tạo tài khoản để lưu lựa chọn và theo dõi các hoạt động của chương trình."}
            </p>
          </div>
          <Link
            className="registry-button registry-button-primary"
            href="/register"
          >
            Tạo tài khoản <UserRound aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
