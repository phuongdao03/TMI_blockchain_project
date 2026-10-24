"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { membershipApi } from "@/lib/api/client";
import type {
  MembershipPlan,
  MembershipPlanCatalog,
  MembershipTier,
} from "@/lib/api/types";

const tiers: {
  code: MembershipTier;
  asset: "bronze" | "silver" | "gold" | "diamond";
  label: string;
}[] = [
  { code: "MEMBER", asset: "bronze", label: "Đồng" },
  { code: "SILVER", asset: "silver", label: "Bạc" },
  { code: "COMPANION", asset: "gold", label: "Vàng" },
  { code: "PRESTIGE", asset: "diamond", label: "Kim cương" },
];

const faqs = [
  {
    question: "Hội viên khác gì tài khoản miễn phí?",
    answer:
      "Đồng là hạng miễn phí dành cho tài khoản thông thường. Các hạng trả phí bổ sung nội dung, chương trình và không gian kết nối theo quyền lợi được công bố.",
  },
  {
    question: "Tôi có thể nâng cấp bất kỳ lúc nào không?",
    answer:
      "Bạn có thể xem các lựa chọn trong tài khoản hội viên. Hệ thống hiển thị báo giá nâng cấp và khoản tín dụng thời gian còn lại trước khi bạn xác nhận thanh toán.",
  },
  {
    question: "Phí hội viên có bao gồm phí nộp hồ sơ đề cử không?",
    answer:
      "Không. Phí hội viên và các khoản phí thẩm định hồ sơ đề cử là hai khoản riêng biệt.",
  },
  {
    question: "Kim cương có đồng nghĩa được công nhận Tinh Hoa Việt không?",
    answer:
      "Không. Kim cương không đồng nghĩa với chứng nhận Tinh Hoa Việt; đây là hạng hội viên cộng đồng, hoàn toàn tách biệt với quy trình thẩm định và công nhận.",
  },
  {
    question: "Tôi có được tham gia tất cả sự kiện không?",
    answer:
      "Không. Quyền đăng ký tùy theo cấp hội viên, quyền lợi còn lại trong chu kỳ, điều kiện của chương trình và số chỗ còn trống. Một số hoạt động có thể có điều kiện hoặc khoản phí riêng.",
  },
  {
    question: "Nếu gói hết hạn thì sao?",
    answer:
      "Khi gói trả phí hết hạn, quyền lợi và quyền truy cập dành riêng cho gói kết thúc; tài khoản trở về cấp Đồng. Tài khoản, hồ sơ, bài viết và lịch sử giao dịch hợp lệ vẫn được giữ.",
  },
  {
    question: "Tôi có thể gia hạn bằng ví không?",
    answer:
      "Có. Bạn chủ động chọn gói, xem giá và xác nhận thanh toán bằng số dư ví nội bộ. Gói không tự động gia hạn và hệ thống không tự động trừ tiền.",
  },
  {
    question: "Nếu đã mua Vàng, muốn lên Kim cương sẽ tính phí thế nào?",
    answer:
      "Bạn gửi yêu cầu xét duyệt Kim cương trước. Nếu được duyệt, hệ thống hiển thị báo giá sau khi tính khoản tín dụng thời gian còn lại theo chính sách; bạn chỉ thanh toán sau khi xem và xác nhận số tiền.",
  },
];

export function MembershipPricingPage() {
  const catalog = useQuery({
    queryKey: ["membership-plan-catalog"],
    queryFn: membershipApi.plans,
    staleTime: 60_000,
  });
  const planByTier = new Map(
    (catalog.data?.plans ?? []).map((plan) => [plan.tier, plan]),
  );
  const ownBenefitsByTier: Record<MembershipTier, string[]> = {
    MEMBER: catalog.data?.member?.benefits ?? [],
    SILVER: planByTier.get("SILVER")?.benefits ?? [],
    COMPANION: planByTier.get("COMPANION")?.benefits ?? [],
    PRESTIGE: planByTier.get("PRESTIGE")?.benefits ?? [],
  };
  const benefitsByTier: Record<MembershipTier, string[]> = {
    MEMBER: [...new Set(ownBenefitsByTier.MEMBER)],
    SILVER: [
      ...new Set([
        ...ownBenefitsByTier.MEMBER,
        ...ownBenefitsByTier.SILVER,
      ]),
    ],
    COMPANION: [
      ...new Set([
        ...ownBenefitsByTier.MEMBER,
        ...ownBenefitsByTier.SILVER,
        ...ownBenefitsByTier.COMPANION,
      ]),
    ],
    PRESTIGE: [
      ...new Set([
        ...ownBenefitsByTier.MEMBER,
        ...ownBenefitsByTier.SILVER,
        ...ownBenefitsByTier.COMPANION,
        ...ownBenefitsByTier.PRESTIGE,
      ]),
    ],
  };

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <header className="rounded-3xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-5 py-9 sm:px-10 sm:py-12">
        <p className="text-xs font-bold tracking-[0.22em] text-[var(--theme-accent)] sm:text-sm">
          CỘNG ĐỒNG HỘI VIÊN
        </p>
        <h1 className="mt-4 max-w-4xl text-3xl font-bold tracking-tight text-[var(--theme-text)] sm:text-5xl">
          HỘI VIÊN TINH HOA VIỆT
        </h1>
        <p className="mt-4 max-w-3xl text-lg font-semibold leading-8 text-[var(--theme-text)] sm:text-xl">
          Kết nối giá trị – Đồng hành phát triển – Lan tỏa tinh hoa.
        </p>
        <p className="mt-3 max-w-3xl leading-7 text-[var(--theme-muted)]">
          Tham gia cộng đồng Tinh Hoa Việt để kết nối những người có chung mối
          quan tâm, tiếp cận chương trình chuyên đề và mở rộng cơ hội hợp tác.
        </p>
        <Link
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-[var(--theme-accent)] px-5 py-2.5 font-semibold text-[var(--theme-accent-contrast)] transition hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href="#membership-tiers"
        >
          Xem các hạng hội viên
        </Link>
      </header>

      <section
        aria-labelledby="membership-tiers-heading"
        className="mt-10 sm:mt-14"
        id="membership-tiers"
      >
        <div className="max-w-3xl">
          <p className="text-sm font-semibold text-[var(--theme-accent)]">
            BỐN CẤP HỘI VIÊN
          </p>
          <h2
            className="mt-2 text-2xl font-bold tracking-tight text-[var(--theme-text)] sm:text-3xl"
            id="membership-tiers-heading"
          >
            Chọn cách bạn đồng hành
          </h2>
          <p className="mt-3 leading-7 text-[var(--theme-muted)]">
            Mỗi cấp mở ra những quyền lợi phù hợp, từ không gian cộng đồng chung
            đến các chương trình kết nối chuyên sâu.
          </p>
        </div>

        {catalog.isPending ? (
          <p className="mt-6 rounded-xl border border-[var(--theme-border)] p-5 text-[var(--theme-muted)]" role="status">
            Đang tải bảng giá hội viên…
          </p>
        ) : null}
        {catalog.isError ? (
          <div
            className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[var(--theme-border)] p-5"
            role="alert"
          >
            <p>
              Bảng giá hội viên hiện chưa kết nối được. Giá và quyền lợi sẽ hiện
              đầy đủ sau khi tải lại dữ liệu.
            </p>
            <button
              className="min-h-11 rounded-lg border border-[var(--theme-border)] px-4 font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              onClick={() => void catalog.refetch()}
              type="button"
            >
              Thử lại bảng giá
            </button>
          </div>
        ) : null}

        <div className="mt-6 grid grid-cols-1 items-stretch gap-4 sm:grid-cols-2 2xl:grid-cols-4">
          {tiers.map((tier) => (
            <PricingCard
              key={tier.code}
              loading={catalog.isPending}
              plan={
                tier.code === "MEMBER" ? undefined : planByTier.get(tier.code)
              }
              freeTier={tier.code === "MEMBER" ? catalog.data?.member : undefined}
              loadError={catalog.isError}
              tier={tier}
            />
          ))}
        </div>
      </section>

      <ComparisonSection benefitsByTier={benefitsByTier} />
      <FaqSection />

      <aside className="mt-10 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-5 text-sm leading-6 text-[var(--theme-muted)] sm:mt-14 sm:p-7">
        Cấp hội viên thể hiện quyền tham gia và sử dụng dịch vụ cộng đồng. Không
        phải chứng nhận chuyên môn hoặc danh hiệu được xác lập thông qua thẩm
        định. Kim cương không làm thay đổi quy trình thẩm định hồ sơ đề cử.
      </aside>
    </main>
  );
}

function PricingCard({
  tier,
  plan,
  freeTier,
  loading,
  loadError,
}: {
  tier: (typeof tiers)[number];
  plan?: MembershipPlan;
  freeTier?: MembershipPlanCatalog["member"];
  loading: boolean;
  loadError: boolean;
}) {
  const isFree = tier.code === "MEMBER";
  const isAvailable =
    isFree || (!loading && !loadError && Boolean(plan?.active));
  const packageName = loadError
    ? "Chưa tải được thông tin gói"
    : isFree
      ? freeTier?.name ?? "Đang tải gói"
      : loading
        ? "Đang tải gói"
        : plan?.active
          ? plan.name
          : "Đang cập nhật";
  const amount = loadError
    ? "Chưa tải được biểu phí"
    : isFree
      ? "Miễn phí"
      : loading
        ? "Đang tải giá"
        : plan?.active
          ? `${formatVnd(plan.amountMinor)}đ`
          : "Chưa mở đăng ký";
  const period = loading
    ? ""
    : plan?.durationDays === 365
      ? "/năm"
      : plan
        ? `/${plan.durationDays} ngày`
        : "";
  const benefits = isFree
    ? (freeTier?.benefits ?? [])
    : (plan?.benefits ?? []);
  const visibleBenefits = benefits.slice(0, 3);
  const description = loadError
    ? "Thông tin giới thiệu và quyền lợi tạm thời chưa tải được."
    : isFree
      ? freeTier?.description
      : plan?.description;
  const conditions = loadError
    ? "Vui lòng tải lại bảng giá để xem điều kiện áp dụng."
    : isFree
      ? freeTier?.conditions
      : plan?.conditions;

  return (
    <article
      aria-labelledby={`${tier.code}-tier-title ${tier.code}-plan-name`}
        className={`flex h-full flex-col rounded-2xl border bg-[var(--theme-surface)] p-4 sm:p-5 ${tier.code === "COMPANION" ? "border-amber-600/60 ring-1 ring-amber-600/25" : "border-[var(--theme-border)]"}`}
    >
      <div className="flex min-h-7 items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--theme-muted)]">
          {tier.label}
        </span>
        {tier.code === "COMPANION" ? (
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-950">
            Được đề xuất
          </span>
        ) : null}
      </div>
      <Image
        alt={`Huy hiệu cấp ${tier.label}`}
        className="mt-3 h-[96px] w-full object-contain sm:h-[112px]"
        height={267}
        sizes="(max-width: 639px) 100vw, (max-width: 1279px) 50vw, 25vw"
        src={`/assets/membership/pricing/${tier.asset}.png`}
        width={800}
      />
      <h3
        className="mt-4 text-xl font-bold text-[var(--theme-text)]"
        id={`${tier.code}-tier-title`}
      >
        {tier.label}
      </h3>
      <p
        className="mt-1 text-base font-semibold text-[var(--theme-text)]"
        id={`${tier.code}-plan-name`}
      >
        {packageName}
      </p>
      <p className="mt-2 min-h-12 text-sm leading-6 text-[var(--theme-muted)]">
        {description}
      </p>
      <p className="mt-5 text-2xl font-bold tracking-tight text-[var(--theme-text)]">
        {amount}
        {period ? (
          <span className="ml-1 text-sm font-medium text-[var(--theme-muted)]">
            {period}
          </span>
        ) : null}
      </p>

      <div className="mt-5 flex-1 border-t border-[var(--theme-border)] pt-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--theme-muted)]">
          {isFree ? "Quyền lợi" : "Quyền lợi bổ sung"}
        </p>
        {!isFree ? (
          <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
            Giữ quyền lợi các hạng thấp hơn và mở khóa quyền lợi riêng.
          </p>
        ) : null}
        {visibleBenefits.length ? (
          <ul className="mt-3 space-y-3">
            {visibleBenefits.map((benefit) => (
              <li className="flex gap-2 text-sm leading-6" key={benefit}>
                <span
                  aria-hidden="true"
                  className="mt-0.5 text-emerald-600"
                >
                  <Check aria-hidden="true" className="size-4 stroke-[2.5]" />
                </span>
                <span>{benefit}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)]">
            {loadError
              ? "Quyền lợi chưa tải được từ danh mục hội viên."
              : "Quyền lợi đang được cập nhật."}
          </p>
        )}
      </div>

        {benefits.length > visibleBenefits.length || conditions ? (
          <details className="mt-4 rounded-lg border border-[var(--theme-border)] px-3 py-2">
            <summary className="min-h-10 cursor-pointer py-2 text-sm font-semibold text-[var(--theme-text)] focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]">
              Xem đủ {benefits.length} quyền lợi và điều kiện
            </summary>
            {benefits.length > visibleBenefits.length ? (
              <ul className="space-y-3 pb-3 pt-1">
                {benefits.slice(visibleBenefits.length).map((benefit) => (
                  <li className="flex gap-2 text-sm leading-6" key={benefit}>
                    <Check
                      aria-hidden="true"
                      className="mt-1 size-4 shrink-0 text-emerald-600"
                    />
                    <span>{benefit}</span>
                  </li>
                ))}
              </ul>
            ) : null}
            {conditions ? (
              <p className="border-t border-[var(--theme-border)] py-3 text-xs leading-5 text-[var(--theme-muted)]">
                {conditions}
              </p>
            ) : null}
          </details>
        ) : null}
      {isAvailable ? (
        <Link
          className="mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-[var(--theme-accent)] px-4 py-2 text-center text-sm font-semibold text-[var(--theme-accent)] transition hover:bg-[var(--theme-accent)] hover:text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
          href={isFree ? "/register?next=%2Fmembership" : "/membership"}
        >
          {isFree
            ? "Tạo tài khoản"
            : tier.code === "PRESTIGE"
              ? "Xem bước xét duyệt"
              : "Đăng ký qua ví"}
        </Link>
      ) : (
        <p className="mt-5 inline-flex min-h-11 items-center justify-center rounded-lg border border-[var(--theme-border)] px-4 py-2 text-center text-sm font-semibold text-[var(--theme-muted)]">
          {loadError
            ? "Chưa xác định trạng thái gói"
            : "Gói chưa mở bán"}
        </p>
      )}
    </article>
  );
}

function ComparisonSection({
  benefitsByTier,
}: {
  benefitsByTier: Record<MembershipTier, string[]>;
}) {
  const comparisonRows = [...new Set(Object.values(benefitsByTier).flat())];
  return (
    <section aria-labelledby="membership-comparison-heading" className="mt-12 sm:mt-16">
      <h2
        className="text-2xl font-bold tracking-tight text-[var(--theme-text)] sm:text-3xl"
        id="membership-comparison-heading"
      >
        So sánh quyền lợi
      </h2>
      <p className="mt-3 max-w-3xl leading-7 text-[var(--theme-muted)]">
        Quyền lợi theo chu kỳ hội viên; quyền đăng ký sự kiện còn phụ thuộc điều
        kiện và số chỗ được công bố.
      </p>

      {comparisonRows.length === 0 ? (
        <p
          className="mt-5 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 text-[var(--theme-muted)]"
          role="status"
        >
          Chưa có dữ liệu quyền lợi để hiển thị bảng so sánh. Vui lòng tải lại
          bảng giá.
        </p>
      ) : (
        <>
          <div className="mt-5 space-y-3 xl:hidden">
            {tiers.map((tier) => (
              <details
                className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"
                key={tier.code}
              >
                <summary className="cursor-pointer font-semibold text-[var(--theme-text)] focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]">
                  {tier.label}
                </summary>
                <ul className="mt-4 space-y-3">
                  {comparisonRows.map((row) => {
                    const value = benefitsByTier[tier.code].includes(row);
                    return (
                      <li
                        className="flex items-start justify-between gap-4 border-t border-[var(--theme-border)] pt-3 text-sm"
                        key={row}
                      >
                        <span className="text-[var(--theme-muted)]">{row}</span>
                        <BenefitStatus available={value} />
                      </li>
                    );
                  })}
                </ul>
              </details>
            ))}
          </div>

          <div className="mt-5 hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] xl:block">
            <table className="w-full border-collapse text-left text-sm">
              <caption className="sr-only">
                So sánh quyền lợi của bốn hạng hội viên Tinh Hoa Việt
              </caption>
              <thead>
                <tr className="border-b border-[var(--theme-border)]">
                  <th className="w-[40%] p-4 font-semibold" scope="col">
                    Quyền lợi
                  </th>
                  {tiers.map((tier) => (
                    <th className="p-4 font-semibold" key={tier.code} scope="col">
                      {tier.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr className="border-b last:border-0" key={row}>
                    <th className="p-4 font-medium" scope="row">
                      {row}
                    </th>
                    {tiers.map((tier) => {
                      const value = benefitsByTier[tier.code].includes(row);
                      return (
                        <td className="p-4 text-[var(--theme-muted)]" key={tier.code}>
                          <BenefitStatus available={value} />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function BenefitStatus({ available }: { available: boolean }) {
  const Icon = available ? Check : X;
  return (
    <span
      aria-label={available ? "Có quyền lợi" : "Chưa có quyền lợi"}
      className={`inline-flex shrink-0 items-center justify-center ${available ? "text-emerald-600" : "text-rose-600"}`}
      role="img"
    >
      <Icon aria-hidden="true" className="size-5 stroke-[2.5]" />
    </span>
  );
}

function FaqSection() {
  return (
    <section aria-labelledby="membership-faq-heading" className="mt-12 sm:mt-16">
      <h2
        className="text-2xl font-bold tracking-tight text-[var(--theme-text)] sm:text-3xl"
        id="membership-faq-heading"
      >
        Câu hỏi thường gặp
      </h2>
      <div className="mt-5 divide-y divide-[var(--theme-border)] border-y border-[var(--theme-border)]">
        {faqs.map((faq) => (
          <details className="py-4" key={faq.question}>
            <summary className="cursor-pointer py-1 font-semibold text-[var(--theme-text)] focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]">
              {faq.question}
            </summary>
            <p className="max-w-4xl pt-3 leading-7 text-[var(--theme-muted)]">
              {faq.answer}
            </p>
          </details>
        ))}
      </div>
      <Link
        className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-[var(--theme-accent)] px-5 py-2.5 font-semibold text-[var(--theme-accent-contrast)] transition hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
        href="/membership"
      >
        Vào tài khoản hội viên
      </Link>
    </section>
  );
}

function formatVnd(amountMinor: number): string {
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 }).format(
    amountMinor,
  );
}
