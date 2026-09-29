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
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
            Ứng dụng Tinh Hoa Việt
          </p>
          <h1 className="mt-4 text-4xl font-bold tracking-[-0.04em] text-white sm:text-6xl">
            Cài đặt trong vài bước
          </h1>
          <p className="mt-5 text-base leading-7 text-slate-300 sm:text-lg">
            Mở trang này trên thiết bị bạn muốn sử dụng, sau đó chọn cách cài
            phù hợp bên dưới. Biểu tượng Tinh Hoa Việt sẽ xuất hiện trên màn
            hình chính hoặc trong danh sách ứng dụng sau khi cài thành công.
          </p>
        </header>

        <section className="mt-10 grid overflow-hidden border-y border-[var(--theme-border)] lg:grid-cols-2">
          <div className="p-5 sm:p-8 lg:p-10">
            <h2 className="text-xl font-bold text-white">
              Cài từ nút trên trang
            </h2>
            <ul className="mt-5 space-y-4 text-sm leading-6 text-slate-300">
              {[
                "Dùng trình duyệt trên chính điện thoại hoặc máy tính muốn cài.",
                "Chọn Tiến hành cài đặt và xác nhận nếu trình duyệt hiện hộp thoại.",
                "Nếu không có hộp thoại, làm theo hướng dẫn thủ công bên cạnh.",
              ].map((item) => (
                <li className="flex gap-3" key={item}>
                  <Check className="mt-1 size-4 shrink-0 text-gold-300" />
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-8 border-t border-[var(--theme-border)] pt-7">
              <PwaInstallAction />
            </div>
          </div>

          <div className="border-t border-[var(--theme-border)] bg-[var(--theme-surface-soft)] p-5 sm:p-8 lg:border-l lg:border-t-0 lg:p-10">
            <h2 className="text-xl font-bold text-white">Cài theo thiết bị</h2>
            <ol className="mt-6 space-y-6">
              <InstallStep icon={Share} title="iPhone hoặc iPad">
                Mở website trong Safari, chạm Chia sẻ, chọn Thêm vào Màn hình
                chính rồi xác nhận Thêm.
              </InstallStep>
              <InstallStep icon={SquarePlus} title="Điện thoại Android">
                Mở menu trình duyệt, chọn Cài đặt ứng dụng hoặc Thêm vào màn
                hình chính, rồi xác nhận.
              </InstallStep>
              <InstallStep icon={MonitorSmartphone} title="Máy tính">
                Nếu trình duyệt có mục Cài đặt ứng dụng, chọn mục đó và xác
                nhận. Nếu không thấy, bạn vẫn có thể tiếp tục dùng website.
              </InstallStep>
            </ol>
            <p className="mt-6 text-sm leading-6 text-slate-400">
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
      <span className="grid size-10 shrink-0 place-items-center rounded-full border border-gold-300/35 text-gold-300">
        <Icon className="size-4" />
      </span>
      <div>
        <h3 className="font-bold text-white">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-slate-400">{children}</p>
      </div>
    </li>
  );
}
