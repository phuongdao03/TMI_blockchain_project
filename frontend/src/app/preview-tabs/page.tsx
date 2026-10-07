import { ExternalLink } from "lucide-react";
import { notFound } from "next/navigation";

const rolePreviews = [
  {
    label: "Khách xem",
    role: "VIEWER",
    description: "Khám phá đề cử và tra cứu thông tin công khai.",
  },
  {
    label: "Người dùng",
    role: "USER",
    description: "Theo dõi hồ sơ và bằng xác lập của mình.",
  },
  {
    label: "Moderator",
    role: "MODERATOR",
    description: "Xem hàng đợi và công việc thẩm định.",
  },
  {
    label: "Super Admin",
    role: "SUPER_ADMIN",
    description: "Xem bảng điều hành và quản trị hệ thống.",
  },
] as const;

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
  if (process.env.NODE_ENV !== "development") notFound();

  const showMockScreens = process.env.AUTH_E2E_SHIM === "true";

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
          Mỗi vai trò mở trong một tab riêng với dữ liệu minh họa, không cần
          đăng nhập.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {rolePreviews.map((preview) => (
            <a
              className="flex min-h-36 flex-col justify-between rounded-2xl border border-[#dac6ad] bg-white p-5 text-[#5b0712] shadow-sm transition-colors hover:border-[#ad7b30] hover:bg-[#fff8e7] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8b4c16]"
              href={`/ui-preview?role=${preview.role}`}
              key={preview.role}
              rel="noopener noreferrer"
              target="_blank"
            >
              <span className="flex items-center justify-between gap-3 font-serif text-xl font-bold">
                {preview.label}
                <ExternalLink aria-hidden="true" className="size-4" />
              </span>
              <span className="mt-3 text-sm leading-relaxed text-[#66524a]">
                {preview.description}
              </span>
            </a>
          ))}
        </div>
        {showMockScreens ? (
          <section className="mt-12" aria-labelledby="mock-screens-heading">
            <h2
              className="font-serif text-2xl font-bold"
              id="mock-screens-heading"
            >
              Các màn hình dùng dữ liệu mẫu
            </h2>
            <div className="mt-5 grid gap-5 lg:grid-cols-3">
              {sections.map((section) => (
                <section
                  key={section.title}
                  className="rounded-2xl border border-[#dac6ad] bg-white p-5 shadow-sm"
                >
                  <h3 className="font-serif text-xl font-bold text-[#5b0712]">
                    {section.title}
                  </h3>
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
          </section>
        ) : null}
      </div>
    </main>
  );
}
