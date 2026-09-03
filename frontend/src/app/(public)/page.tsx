import {
  ArrowRight,
  BookOpenText,
  ScanSearch,
  Landmark,
  Search,
  BadgeCheck,
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
  {
    number: "01",
    title: "Khám phá đề cử",
    detail:
      "Tìm tác phẩm, thương hiệu hoặc sáng kiến theo lĩnh vực và bắt đầu từ phần giới thiệu ngắn gọn.",
    href: "/works",
    action: "Khám phá đề cử",
    icon: ScanSearch,
  },
  {
    number: "02",
    title: "Đọc câu chuyện & hồ sơ",
    detail:
      "Hiểu bối cảnh, chủ thể và các thông tin được phép công bố kèm theo từng đề cử.",
    href: "/process",
    action: "Xem quy trình",
    icon: BookOpenText,
  },
  {
    number: "03",
    title: "Kiểm chứng thông tin",
    detail:
      "Tra cứu chứng thư khi hồ sơ đã được xác lập để đối chiếu mã, trạng thái và dữ liệu xác thực.",
    href: "/verify",
    action: "Tra cứu chứng thư",
    icon: BadgeCheck,
  },
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
        <div className="mx-auto grid max-w-[100rem] items-center gap-8 px-4 py-10 sm:px-6 sm:py-14 lg:min-h-[calc(100dvh-4.5rem)] lg:grid-cols-[0.88fr_1.12fr] lg:gap-5 lg:px-8 lg:py-16 xl:px-14">
          <div className="relative z-10 max-w-[44rem] lg:py-8">
            <p className="registry-kicker">
              <span aria-hidden="true" className="registry-kicker-dot" />
              Đề cử Tinh Hoa Việt
            </p>
            <h1 className="mt-7 text-[clamp(2.35rem,10vw,5.65rem)] font-semibold leading-[0.98] tracking-[-0.055em] text-balance sm:mt-10">
              Nơi những giá trị Việt được giới thiệu,{" "}
              <span className="text-gold-300">ghi nhận và lan tỏa.</span>
            </h1>
            <p className="mt-8 max-w-[41rem] text-base leading-8 text-slate-300 sm:text-lg">
              Khám phá các đề cử tiêu biểu, đọc câu chuyện phía sau mỗi giá trị
              và tra cứu thông tin, trạng thái cùng bằng chứng xác thực của các
              hồ sơ được công bố.
            </p>
            <p className="mt-4 flex max-w-[41rem] items-start gap-2 text-sm leading-6 text-slate-300">
              <ShieldCheck
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0 text-gold-300"
              />
              Blockchain chỉ ghi dấu vân tay số để kiểm tra thay đổi; tài liệu
              gốc vẫn được lưu an toàn trong kho của hệ thống.
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
            <dl className="registry-hero__summary mt-8 grid grid-cols-3 border-t border-white/15 pt-6 text-sm">
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
          <div className="registry-visual relative hidden min-w-0 self-stretch sm:flex lg:-mr-14">
            <CertificateOrbit />
          </div>
        </div>
      </section>

      <section className="home-journey journey-workflow border-b">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
          <div className="journey-workflow__intro">
            <p className="registry-section-label">Hành trình minh bạch</p>
            <h2 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-5xl">
              Xem giá trị Việt theo ba bước rõ ràng.
            </h2>
            <p className="mt-6 max-w-lg leading-7 text-slate-400">
              Mỗi đề cử được trình bày cùng câu chuyện, dữ liệu công khai và
              trạng thái xác thực để bạn dễ theo dõi từ đầu đến cuối.
            </p>
          </div>
          <ol className="journey-workflow__cards">
            {journey.map(
              ({ action, detail, href, icon: Icon, number, title }) => (
                <li key={number}>
                  <Link className="journey-workflow__card" href={href}>
                    <div
                      aria-hidden="true"
                      className={`journey-workflow__visual journey-workflow__visual--${number}`}
                    >
                      <span className="journey-workflow__number">{number}</span>
                      <span className="journey-workflow__icon-frame">
                        <Icon
                          className="journey-workflow__icon"
                          strokeWidth={1.6}
                        />
                      </span>
                      <span className="journey-workflow__seal" />
                      <span className="journey-workflow__grid" />
                    </div>
                    <div className="journey-workflow__body">
                      <h3>{title}</h3>
                      <p>{detail}</p>
                      <span className="journey-workflow__action">
                        {action} <ArrowRight aria-hidden="true" />
                      </span>
                    </div>
                  </Link>
                </li>
              ),
            )}
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
            <Link className="text-sm font-bold text-primary-700" href="/works">
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
            <ShieldCheck
              aria-hidden="true"
              className="size-6 text-primary-700"
            />
            <h2 className="mt-5 text-3xl font-semibold tracking-tight">
              {preview
                ? "Muốn theo dõi hành trình Tinh Hoa Việt?"
                : "Tiếp tục khám phá Tinh Hoa Việt"}
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              {preview
                ? "Tạo tài khoản để lưu nội dung quan tâm và theo dõi các cập nhật chính thức của chương trình."
                : "Tạo tài khoản để gửi hồ sơ, nhận phản hồi và quản lý thông tin của bạn."}
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
