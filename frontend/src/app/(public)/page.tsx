import {
  ArrowRight,
  BookOpenText,
  ScanSearch,
  Landmark,
  Search,
  BadgeCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";

import {
  HomeClosingAccountCta,
  HomeHeroAccountActions,
  HomeHeroAccountMessage,
} from "@/components/public/home-account-experience";
import { FeaturedAssets } from "@/components/public/featured-assets";
import {
  InstitutionContent,
  ProposalSection,
} from "@/components/public/institution-content";
import { HeritageSymbols } from "@/components/public/heritage-symbols";
import { MissionContent } from "@/components/public/mission-content";
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
      "Tra cứu bằng xác lập khi hồ sơ đã được xác lập để đối chiếu mã, trạng thái và dữ liệu xác thực.",
    href: "/verify",
    action: "Tra cứu bằng xác lập",
    icon: BadgeCheck,
  },
] as const;

import "@/components/public/home-editorial.css";

export default function HomePage() {
  const preview = isPreviewRelease();
  return (
    <div className="public-home home-editorial">
      <section
        className="registry-hero relative border-b border-white/10"
        id="gioi-thieu"
      >
        <Image
          className="home-intro__drum"
          alt=""
          aria-hidden="true"
          src="/assets/brand/trong-dong.png"
          width={640}
          height={640}
          sizes="320px"
          loading="lazy"
        />
        <div className="registry-hero-glow" aria-hidden="true" />
        <div className="registry-hero__layout mx-auto max-w-[100rem] px-4 py-8 sm:px-6 sm:py-14 lg:min-h-[calc(100dvh-4.5rem)] lg:px-8 lg:py-16 xl:px-14">
          <div className="registry-hero__intro relative z-10 max-w-[44rem] lg:pt-8">
            <h1 className="mt-7 text-3xl font-semibold leading-tight tracking-[-0.04em] text-balance sm:mt-10 sm:text-4xl">
              Suy tôn trí tuệ.{" "}
              <span className="text-gold-300">Lưu truyền di sản.</span>
            </h1>
            <HomeHeroAccountMessage />
            <p className="registry-hero__copy--desktop mt-5 max-w-[41rem] text-[0.95rem] leading-7 text-slate-300 sm:mt-8 sm:text-lg sm:leading-8">
              Tinh Hoa Việt giới thiệu những giá trị tiêu biểu của con người, tổ
              chức, tri thức, văn hóa và sáng tạo Việt Nam qua hồ sơ có căn cứ.
              <span className="home-intro__extended">
                {" "}
                Tại đây, công chúng có thể khám phá đề cử, theo dõi trạng thái
                xác lập và đối chiếu thông tin được công bố.
              </span>
            </p>
          </div>
          <div className="registry-visual registry-visual--heritage relative min-w-0 self-stretch lg:-mr-14">
            <HeritageSymbols />
          </div>
          <div className="registry-hero__actions relative z-10 max-w-[44rem] lg:pb-8">
            <div className="registry-hero__action-row">
              <HomeHeroAccountActions preview={preview} />
              <Link
                className="registry-hero__discover registry-button registry-button-secondary"
                href="/works"
              >
                Khám phá đề cử
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
              <Link className="registry-hero__document-link" href="/process">
                Xem quy trình
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
              <Link
                className="registry-hero__document-link"
                href="#van-ban-thanh-lap"
              >
                Xem văn bản thành lập
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </div>
            <form
              action="/works"
              aria-label="Tra cứu đề cử từ phần giới thiệu"
              className="registry-hero__desktop-search registry-search mt-6"
              role="search"
            >
              <Search
                aria-hidden="true"
                className="size-5 shrink-0 text-slate-500"
              />
              <label className="sr-only" htmlFor="registry-hero-search-input">
                Tìm theo tên, câu chuyện hoặc lĩnh vực
              </label>
              <input
                id="registry-hero-search-input"
                name="query"
                placeholder="Tìm kiếm đề cử"
              />
              <button type="submit">Tra cứu</button>
            </form>
            <dl className="registry-hero__summary mt-8 grid grid-cols-3 border-t border-white/15 pt-6 text-sm">
              {[
                ["Đề cử", "Theo tiêu chí"],
                ["Xác lập", "Theo quyết định"],
                ["Tra cứu", "Có thể đối chiếu"],
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
          <div className="registry-hero__provenance">
            <span className="registry-hero__provenance-label">
              Thông tin thành lập
            </span>
            <p className="registry-hero__organization">
              Trung tâm Xác lập Tinh Hoa Việt trực thuộc Viện Những Vấn đề Phát
              triển (VIDS), được thành lập theo Quyết định số 55 ngày
              02/01/2026.
            </p>
          </div>
        </div>
      </section>

      <InstitutionContent />
      <MissionContent />
      <HomeAudiences />
      <HomeFeatured preview={preview} />
      <HomeJourney />
      <ProposalSection />
      <section
        className="home-community"
        aria-labelledby="home-community-title"
      >
        <div className="home-community__heading">
          <p className="institution-eyebrow">Cộng đồng và đồng hành</p>
          <h2 id="home-community-title">
            Kết nối hôm nay.
            <br />
            <span>Tiếp nối giá trị Việt.</span>
          </h2>
          <p>
            Mỗi câu chuyện được chia sẻ, mỗi người cùng đồng hành đều góp thêm
            một dấu ấn cho hành trình Tinh Hoa Việt.
          </p>
        </div>
        <nav className="home-community__paths" aria-label="Tham gia cộng đồng">
          <Link className="home-community__path" href="/community">
            <div className="home-community__photo">
              <Image
                alt="Hoạt động kết nối trong bộ sưu tập Tinh Hoa Việt"
                src="/assets/institution/gallery-05-large.webp"
                fill
                sizes="(max-width: 48rem) 90vw, 550px"
              />
            </div>
            <div className="home-community__path-copy">
              <span className="institution-eyebrow">Chia sẻ và kết nối</span>
              <h3>Câu chuyện từ cộng đồng</h3>
              <p>
                Gặp gỡ những góc nhìn, hoạt động và giá trị đang được lan tỏa.
              </p>
              <span className="home-community__action">
                Khám phá cộng đồng <ArrowRight aria-hidden="true" size={20} />
              </span>
            </div>
          </Link>
          <Link className="home-community__path" href="/cong-dong/hoi-vien">
            <div className="home-community__photo">
              <Image
                alt="Gặp gỡ và đồng hành cùng các đơn vị Tinh Hoa Việt"
                src="/assets/institution/gallery-03-large.webp"
                fill
                sizes="(max-width: 48rem) 90vw, 550px"
              />
            </div>
            <div className="home-community__path-copy">
              <span className="institution-eyebrow">Cùng nhau tiếp nối</span>
              <h3>Đồng hành cùng Tinh Hoa Việt</h3>
              <p>
                Tìm hiểu cộng đồng hội viên và lựa chọn cách tham gia phù hợp
                với bạn.
              </p>
              <span className="home-community__action">
                Tìm hiểu hội viên <ArrowRight aria-hidden="true" size={20} />
              </span>
            </div>
          </Link>
        </nav>
      </section>

      <HomeClosingAccountCta preview={preview} />
    </div>
  );
}

function HomeJourney() {
  return (
    <section className="home-journey journey-workflow border-b">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="journey-workflow__intro">
          <p className="registry-section-label">Hành trình minh bạch</p>
          <h2 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-5xl">
            Xem giá trị Việt theo ba bước rõ ràng.
          </h2>
          <p className="mt-6 max-w-lg leading-7 text-slate-400">
            Mỗi đề cử được trình bày cùng câu chuyện, dữ liệu công khai và trạng
            thái xác thực để bạn dễ theo dõi từ đầu đến cuối.
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
  );
}

function HomeAudiences() {
  return (
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
  );
}

function HomeFeatured({ preview }: { preview: boolean }) {
  return (
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
        <form
          action="/works"
          aria-label="Tìm kiếm đề cử"
          className="home-featured__search registry-search"
          role="search"
        >
          <Search aria-hidden="true" className="size-5 shrink-0" />
          <label className="sr-only" htmlFor="registry-search-input">
            Tìm theo tên, câu chuyện hoặc lĩnh vực
          </label>
          <input
            id="registry-search-input"
            name="query"
            placeholder="Tác phẩm, chủ đề..."
          />
          <button type="submit">Tìm</button>
        </form>
        <div className="mt-10 text-slate-900">
          <FeaturedAssets />
        </div>
      </div>
    </section>
  );
}
