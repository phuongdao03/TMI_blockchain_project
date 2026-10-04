import { ExternalLink } from "lucide-react";
import { notFound } from "next/navigation";

const sections = [
  {
    title: "Trang công khai",
    description: "Nhận diện, câu chuyện tác phẩm và tra cứu thông tin.",
    links: [
      { label: "Trang giới thiệu", href: "/" },
      {
        label: "Trang tác phẩm và video",
        href: "/works/video-chao-mung-tinh-hoa-viet",
      },
      {
        label: "Trang kiểm tra bằng",
        href: "/verify/demo-token",
      },
    ],
  },
  {
    title: "Người gửi hồ sơ",
    description: "Theo dõi tiến độ, bổ sung tài liệu và xem bằng xác lập.",
    links: [
      { label: "Tổng quan", screen: "applicant-home" },
      { label: "Hồ sơ của tôi", screen: "applicant-dossiers" },
      { label: "Chi tiết hồ sơ", screen: "applicant-dossier" },
      { label: "Tạo hồ sơ", screen: "applicant-new" },
      { label: "Bằng xác lập", screen: "applicant-certificates" },
      { label: "Chi tiết bằng", screen: "applicant-certificate" },
    ],
  },
  {
    title: "Nhân viên quản trị",
    description: "Theo dõi công việc, thẩm định và bằng đã phát hành.",
    links: [
      { label: "Tổng quan vận hành", screen: "admin-home" },
      { label: "Hồ sơ cần xem", screen: "admin-reviews" },
      { label: "Quản lý bằng", screen: "admin-certificates" },
      { label: "Phân công công việc", screen: "admin-work" },
    ],
  },
] as const;

export default function PreviewTabsPage() {
  if (
    process.env.NODE_ENV !== "development" ||
    process.env.AUTH_E2E_SHIM !== "true"
  ) {
    notFound();
  }

  return (
    <main className="min-h-dvh bg-[#fff9f3] px-4 py-8 text-[#241515] sm:px-8">
      <div className="mx-auto max-w-5xl">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8b4c16]">
          Đề cử Tinh Hoa Việt · Bản xem local
        </p>
        <h1 className="mt-3 font-serif text-3xl font-bold sm:text-4xl">
          Xem các giao diện đã sửa
        </h1>
        <p className="mt-3 max-w-3xl text-base leading-relaxed text-[#5b4540]">
          Chọn một màn hình để mở trong tab riêng. Các trang hồ sơ và nhân viên
          dùng dữ liệu mẫu local, tự vào phiên xem nên không cần đăng nhập.
        </p>
        <div className="mt-8 grid gap-5 lg:grid-cols-3">
          {sections.map((section) => (
            <section
              key={section.title}
              className="rounded-2xl border border-[#dac6ad] bg-white p-5 shadow-sm"
            >
              <h2 className="font-serif text-xl font-bold text-[#5b0712]">
                {section.title}
              </h2>
              <p className="mt-2 min-h-14 text-sm leading-relaxed text-[#66524a]">
                {section.description}
              </p>
              <ul className="mt-4 space-y-2">
                {section.links.map((link) => {
                  const href =
                    "href" in link
                      ? link.href
                      : `/local-preview?screen=${link.screen}`;
                  return (
                    <li key={link.label}>
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex min-h-12 items-center justify-between gap-3 rounded-xl border border-[#eee1cf] px-4 py-3 text-sm font-semibold text-[#5b0712] transition-colors hover:border-[#ad7b30] hover:bg-[#fff8e7] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8b4c16]"
                      >
                        <span>{link.label}</span>
                        <ExternalLink
                          aria-hidden="true"
                          className="size-4 shrink-0"
                        />
                      </a>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}
