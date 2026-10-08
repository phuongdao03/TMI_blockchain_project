import type { Metadata } from "next";
import { Check, MonitorSmartphone, Share, SquarePlus } from "lucide-react";
import type { ReactNode } from "react";

import { PwaInstallAction } from "@/components/pwa/pwa-install-button";

export const metadata: Metadata = {
  title: "Hướng dẫn cài ứng dụng",
  description:
    "Các bước thêm Tinh Hoa Việt vào màn hình chính trên điện thoại hoặc máy tính.",
};

export default function InstallPage() {
  return (
    <div className="install-guide public-theme-surface min-h-[calc(100dvh-5rem)] px-4 py-10 sm:px-6 sm:py-16 lg:px-8">
      <main className="mx-auto max-w-5xl">
        <header className="max-w-3xl">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--theme-accent)]">
            Ứng dụng Tinh Hoa Việt
          </p>
          <h1 className="mt-4 text-4xl font-bold tracking-[-0.04em] text-[var(--theme-text)] sm:text-6xl">
            Cài đặt trong vài bước
          </h1>
          <p className="mt-5 text-base leading-7 text-[var(--theme-muted)] sm:text-lg">
            Mở trang trên thiết bị bạn muốn dùng rồi nhấn Tải ứng dụng. Chrome
            hoặc Edge sẽ mở hộp thoại cài khi cho phép; nếu chưa hiện, làm theo
            hướng dẫn bên dưới. Trên iPhone và iPad, hãy dùng menu Chia sẻ của
            Safari.
          </p>
        </header>

        <section className="mt-10 grid overflow-hidden border-y border-[var(--theme-border)] lg:grid-cols-2">
          <div className="p-5 sm:p-8 lg:p-10">
            <h2 className="text-xl font-bold text-[var(--theme-text)]">
              Cài theo trình duyệt của bạn
            </h2>
            <ul className="mt-5 space-y-4 text-sm leading-6 text-[var(--theme-muted)]">
              {[
                "Mở trang bằng Chrome hoặc Edge trên chính thiết bị muốn cài, không dùng chế độ ẩn danh.",
                "Nhấn Tải ứng dụng; nếu chưa có hộp thoại, dùng mục cài ứng dụng trong menu trình duyệt.",
                "Trên iPhone hoặc iPad, làm theo các bước trong Safari bên cạnh.",
              ].map((item) => (
                <li className="flex gap-3" key={item}>
                  <Check className="mt-1 size-4 shrink-0 text-[var(--theme-accent)]" />
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-8 border-t border-[var(--theme-border)] pt-7">
              <PwaInstallAction />
            </div>
          </div>

          <div
            id="install-device-steps"
            className="scroll-mt-28 border-t border-[var(--theme-border)] bg-[var(--theme-surface-soft)] p-5 sm:p-8 lg:border-l lg:border-t-0 lg:p-10"
          >
            <h2 className="text-xl font-bold text-[var(--theme-text)]">
              Hướng dẫn theo thiết bị
            </h2>
            <ol className="mt-6 space-y-6">
              <InstallStep icon={Share} title="iPhone hoặc iPad">
                Mở website trong Safari, chạm Chia sẻ, chọn Thêm vào Màn hình
                chính, bật Mở dưới dạng ứng dụng nếu có, rồi chạm Thêm.
              </InstallStep>
              <InstallStep icon={SquarePlus} title="Điện thoại Android">
                Trong Chrome, chạm ⋮ → Cài đặt và tạo lối tắt → Cài đặt. Tùy
                phiên bản, mục này có thể là Cài đặt ứng dụng hoặc Thêm vào màn
                hình chính.
              </InstallStep>
              <InstallStep icon={MonitorSmartphone} title="Máy tính">
                Trong Chrome, chọn ⋮ → Truyền, lưu và chia sẻ → Cài đặt trang
                dưới dạng ứng dụng. Trong Edge, chọn ⋯ → Công cụ khác → Ứng dụng
                → Cài đặt trang này dưới dạng ứng dụng. Bạn cũng có thể chọn
                biểu tượng cài ở thanh địa chỉ nếu thấy.
              </InstallStep>
            </ol>
            <p className="mt-6 text-sm leading-6 text-[var(--theme-muted)]">
              Sau khi cài, mở biểu tượng Tinh Hoa Việt để kiểm tra. Bạn có thể
              gỡ ứng dụng từ thiết bị khi không còn cần dùng.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

function InstallStep({
  children,
  icon: Icon,
  title,
}: {
  children: ReactNode;
  icon: typeof Share;
  title: string;
}) {
  return (
    <li className="flex gap-4">
      <span className="grid size-10 shrink-0 place-items-center rounded-full border border-[var(--theme-border)] text-[var(--theme-accent)]">
        <Icon className="size-4" />
      </span>
      <div>
        <h3 className="font-bold text-[var(--theme-text)]">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
          {children}
        </p>
      </div>
    </li>
  );
}
