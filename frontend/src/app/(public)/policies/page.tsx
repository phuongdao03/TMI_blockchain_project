import { PolicyGuide } from "@/components/public/platform-guidance";

export default function PoliciesPage() {
  return (
    <div className="bg-[#fbf7f0]">
      <header className="border-b border-neutral-200 text-neutral-950">
        <div className="mx-auto max-w-6xl px-4 pt-16 pb-14 sm:px-6 lg:px-8 lg:pt-24 lg:pb-20">
          <p className="text-xs font-semibold tracking-[0.16em] text-primary-700 uppercase">
            Chính sách sử dụng
          </p>
          <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Thông tin của bạn được sử dụng và bảo vệ như thế nào.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-700 sm:text-lg">
            Nội dung dưới đây giải thích phạm vi thu thập, thời gian lưu trữ,
            quyền của bạn và cách liên hệ khi cần xem xét một quyết định.
          </p>
          <p className="mt-6 text-sm text-neutral-700">
            Cập nhật lần cuối: 08/08/2026
          </p>
        </div>
      </header>
      <PolicyGuide />
    </div>
  );
}
