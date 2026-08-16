import { ArrowLeft, BellRing, Sparkles } from "lucide-react";
import Link from "next/link";

const content = {
  voting: {
    eyebrow: "Giai đoạn tiếp theo",
    title: "Bình chọn sẽ sớm ra mắt",
    description:
      "Không gian bình chọn đang được hoàn thiện để mỗi lượt tham gia rõ ràng, công bằng và dễ theo dõi. Hiện tại, bạn có thể khám phá các đề cử đã được công bố.",
  },
  submission: {
    eyebrow: "Đang chuẩn bị mở",
    title: "Cổng gửi đề cử sẽ sớm ra mắt",
    description:
      "Quy trình tiếp nhận đang được hoàn thiện. Khi chính thức mở, hướng dẫn và điều kiện tham gia sẽ được công bố đầy đủ trước khi bạn bắt đầu.",
  },
} as const;

export type ComingSoonFeatureName = keyof typeof content;

export function ComingSoonFeature({
  feature,
}: {
  feature: ComingSoonFeatureName;
}) {
  const item = content[feature];
  return (
    <section className="relative isolate min-h-[calc(100dvh-4.5rem)] overflow-hidden bg-[#f7f2e9] px-4 py-20 text-[#181615] sm:px-6 lg:px-8">
      <div
        aria-hidden="true"
        className="absolute top-[-10rem] right-[-8rem] -z-10 size-[30rem] rounded-full bg-primary-600/10 blur-3xl"
      />
      <div className="mx-auto max-w-4xl border-y border-black/15 py-14 sm:py-20">
        <span className="grid size-12 place-items-center rounded-full bg-primary-600 text-white">
          <Sparkles aria-hidden="true" className="size-5" />
        </span>
        <p className="mt-8 text-xs font-bold tracking-[0.18em] text-primary-700 uppercase">
          {item.eyebrow}
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-balance sm:text-6xl">
          {item.title}
        </h1>
        <p className="mt-6 max-w-2xl text-base leading-8 text-neutral-700 sm:text-lg">
          {item.description}
        </p>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Link
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-md bg-primary-600 px-5 text-sm font-bold text-white hover:bg-primary-700"
            href="/works"
          >
            Khám phá các đề cử
          </Link>
          <Link
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-md border border-black/20 px-5 text-sm font-bold hover:border-primary-600 hover:text-primary-700"
            href="/"
          >
            <ArrowLeft aria-hidden="true" className="size-4" /> Trang chủ
          </Link>
        </div>
        <p className="mt-10 flex items-center gap-2 text-sm text-neutral-600">
          <BellRing aria-hidden="true" className="size-4 text-primary-700" />
          Thông tin mở tính năng sẽ được công bố trên website.
        </p>
      </div>
    </section>
  );
}
