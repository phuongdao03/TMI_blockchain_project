import {
  ArrowRight,
  BadgeCheck,
  Blocks,
  FileCheck2,
  Fingerprint,
  ScanSearch,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { CertificateOrbit } from "@/components/visual/certificate-orbit";
import { FeaturedAssets } from "@/components/public/featured-assets";

const trustPoints = [
  {
    icon: Fingerprint,
    label: "Định danh rõ ràng",
    detail: "Mỗi chủ thể, mỗi vai trò đều được kiểm soát",
  },
  {
    icon: Blocks,
    label: "Bằng chứng blockchain",
    detail: "Dấu thời gian và tính toàn vẹn có thể kiểm tra",
  },
  {
    icon: ScanSearch,
    label: "Xác minh công khai",
    detail: "Tra cứu nguồn gốc mà không lộ dữ liệu nhạy cảm",
  },
] as const;

const workflow = [
  {
    number: "01",
    title: "Thiết lập hồ sơ",
    description:
      "Chuẩn hóa thông tin tài sản, chủ thể và bộ bằng chứng trong một quy trình có kiểm soát.",
    icon: FileCheck2,
  },
  {
    number: "02",
    title: "Thẩm định minh bạch",
    description:
      "Theo dõi trạng thái, trách nhiệm và lịch sử quyết định ở từng mốc nghiệp vụ.",
    icon: ShieldCheck,
  },
  {
    number: "03",
    title: "Phát hành & xác minh",
    description:
      "Neo bằng chứng lên blockchain và cung cấp kênh kiểm tra công khai, độc lập.",
    icon: BadgeCheck,
  },
] as const;

export default function HomePage() {
  return (
    <>
      <section
        className="hero-grid-surface relative isolate overflow-hidden border-b border-white/10"
        id="nen-tang"
      >
        <div className="mx-auto grid min-h-dvh max-w-[90rem] items-center gap-10 px-5 py-16 sm:px-8 sm:py-20 xl:grid-cols-[0.82fr_1.18fr] xl:px-12">
          <div className="relative z-20 max-w-2xl">
            <div className="mb-7 inline-flex min-h-9 items-center gap-2 rounded-full border border-gold-300/20 bg-gold-300/5 px-3 text-xs font-semibold tracking-[0.14em] text-gold-300 uppercase">
              <span className="size-1.5 rounded-full bg-gold-300 shadow-[0_0_14px_var(--color-gold-300)]" />
              Hệ thống đăng bộ &amp; xác minh
            </div>
            <h1 className="max-w-3xl text-4xl leading-[1.08] font-semibold tracking-[-0.04em] text-white sm:text-5xl lg:text-6xl">
              Bằng chứng cho giá trị số,{" "}
              <span className="text-gold-300">
                được thiết kế để kiểm chứng.
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-slate-300 sm:text-lg sm:leading-8">
              TMI tổ chức hồ sơ, thẩm định, chứng thư và dấu vết blockchain
              thành một chuỗi bằng chứng nhất quán—để mỗi giá trị số đều có
              nguồn gốc rõ ràng và có thể đối chiếu độc lập.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-semibold text-white shadow-xl shadow-primary-950/30 hover:bg-primary-500"
                href="/register"
              >
                Khởi tạo hồ sơ
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
              <Link
                className="inline-flex min-h-12 items-center justify-center rounded-lg border border-white/15 bg-white/5 px-5 text-sm font-semibold text-white hover:border-white/25 hover:bg-white/10"
                href="/#quy-trinh"
              >
                Khám phá quy trình
              </Link>
            </div>
            <form
              action="/thu-vien"
              className="mt-5 flex max-w-xl gap-2 rounded-xl border border-white/10 bg-white/5 p-2"
            >
              <label className="flex min-h-11 flex-1 items-center gap-2 px-2">
                <Search className="size-4 text-slate-500" />
                <span className="sr-only">Tra cứu tài sản công khai</span>
                <input
                  className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                  name="query"
                  placeholder="Tra cứu tài sản hoặc số chứng thư"
                />
              </label>
              <button
                className="rounded-lg bg-white px-4 text-sm font-bold text-ink-950"
                type="submit"
              >
                Tra cứu
              </button>
            </form>
            <dl className="mt-10 grid max-w-xl grid-cols-3 gap-4 border-t border-white/10 pt-6">
              <div>
                <dt className="text-xs text-slate-500">Dữ liệu</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-200">
                  Bảo toàn
                </dd>
              </div>
              <div className="border-l border-white/10 pl-4">
                <dt className="text-xs text-slate-500">Trạng thái</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-200">
                  Minh bạch
                </dd>
              </div>
              <div className="border-l border-white/10 pl-4">
                <dt className="text-xs text-slate-500">Xác minh</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-200">
                  Độc lập
                </dd>
              </div>
            </dl>
          </div>

          <CertificateOrbit className="xl:-mr-4" />
        </div>
      </section>

      <section className="border-b border-white/10 bg-ink-950">
        <div className="mx-auto grid max-w-7xl gap-px bg-white/10 sm:grid-cols-3">
          {[
            ["05", "Tiêu chí thẩm định 5T"],
            ["24/7", "Khả năng xác minh công khai"],
            ["01", "Nguồn dữ liệu nhất quán"],
          ].map(([value, label]) => (
            <div className="bg-ink-950 px-6 py-10 lg:px-10" key={label}>
              <strong className="text-4xl font-bold tracking-tight text-gold-300">
                {value}
              </strong>
              <p className="mt-2 text-sm text-slate-400">{label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-b border-white/10 bg-ink-900">
        <div className="mx-auto grid max-w-7xl divide-y divide-white/10 px-4 sm:px-6 md:grid-cols-3 md:divide-x md:divide-y-0 lg:px-8">
          {trustPoints.map(({ icon: Icon, label, detail }) => (
            <div className="flex gap-4 py-6 md:px-6 first:pl-0" key={label}>
              <span className="grid size-10 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/5 text-gold-300">
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <div>
                <h2 className="text-sm font-semibold text-white">{label}</h2>
                <p className="mt-1 text-xs leading-5 text-slate-400">
                  {detail}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-white/10 bg-ink-900">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[0.8fr_1.2fr] lg:px-8 lg:py-28">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
              Phương pháp thẩm định 5T
            </p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-5xl">
              Năm lớp kiểm chứng cho một giá trị đáng tin.
            </h2>
            <Link
              className="mt-7 inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 px-4 text-sm font-bold text-white"
              href="/thu-vien"
            >
              Khám phá tài sản đã xác lập <ArrowRight className="size-4" />
            </Link>
          </div>
          <div className="grid gap-px overflow-hidden rounded-3xl border border-white/10 bg-white/10 sm:grid-cols-2">
            {[
              ["Tính thật", "Đối chiếu nguồn gốc và chủ thể."],
              ["Tính toàn vẹn", "Bảo toàn dữ liệu qua từng phiên bản."],
              ["Tính minh bạch", "Lưu vết quyết định và trách nhiệm."],
              ["Tính thời điểm", "Ghi nhận mốc phát hành có kiểm chứng."],
              ["Tính tin cậy", "Đối chiếu độc lập bằng blockchain."],
            ].map(([title, detail], index) => (
              <article
                className="bg-ink-900 p-6 last:sm:col-span-2"
                key={title}
              >
                <span className="font-mono text-xs text-primary-500">
                  0{index + 1}
                </span>
                <h3 className="mt-5 text-lg font-bold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {detail}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 bg-ink-950">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
          <div className="mb-10 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
                Tài sản tiêu biểu
              </p>
              <h2 className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-5xl">
                Giá trị trong mạng lưới TMI.
              </h2>
            </div>
            <Link className="text-sm font-bold text-white" href="/thu-vien">
              Xem toàn bộ thư viện →
            </Link>
          </div>
          <FeaturedAssets />
        </div>
      </section>

      <section className="bg-background text-neutral-950" id="quy-trinh">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
          <div className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:gap-16">
            <div>
              <p className="text-sm font-semibold tracking-[0.12em] text-primary-700 uppercase">
                Từ dữ liệu đến niềm tin
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">
                Một quy trình. Mỗi bước đều có bằng chứng.
              </h2>
              <p className="mt-5 max-w-lg leading-7 text-neutral-700">
                Kiến trúc nghiệp vụ rõ ràng giúp tổ chức kiểm soát trách nhiệm,
                người dùng theo dõi tiến độ và công chúng xác minh kết quả.
              </p>
            </div>

            <ol className="border-t border-neutral-200">
              {workflow.map(
                ({ number, title, description, icon: Icon }, index) => (
                  <li
                    className="grid gap-4 border-b border-neutral-200 py-6 sm:grid-cols-[4rem_1fr_auto] sm:items-start"
                    key={number}
                  >
                    <span className="font-mono text-sm text-primary-700">
                      {number}
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold">{title}</h3>
                      <p className="mt-2 max-w-xl text-sm leading-6 text-neutral-700">
                        {description}
                      </p>
                    </div>
                    <span className="hidden size-11 place-items-center rounded-full border border-neutral-200 bg-surface text-primary-700 sm:grid">
                      <Icon aria-hidden="true" className="size-5" />
                    </span>
                    {index < workflow.length - 1 ? null : (
                      <span className="sr-only">Bước cuối</span>
                    )}
                  </li>
                ),
              )}
            </ol>
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 bg-ink-950">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-14 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div>
            <p className="text-sm font-semibold text-gold-300">
              Sẵn sàng xây dựng tài sản số đáng tin cậy?
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-white">
              Bắt đầu từ một hồ sơ có bằng chứng.
            </h2>
          </div>
          <Link
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-primary-600 px-5 text-sm font-semibold text-white hover:bg-primary-500"
            href="/register"
          >
            Đăng ký nền tảng
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
