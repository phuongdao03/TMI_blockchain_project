import { WifiOff } from "lucide-react";
import Link from "next/link";

export default function OfflinePage() {
  return (
    <main className="grid min-h-dvh place-items-center bg-[#fffaf3] p-6 text-[#241616]">
      <section className="w-full max-w-lg border-t-4 border-[#8b0000] bg-white p-8 shadow-xl">
        <WifiOff aria-hidden="true" className="size-10 text-[#8b0000]" />
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.18em] text-[#8b0000]">
          Kết nối bị gián đoạn
        </p>
        <h1 className="mt-2 text-3xl font-bold">Bạn đang ngoại tuyến</h1>
        <p className="mt-4 leading-7 text-[#685858]">
          Hãy kiểm tra kết nối mạng rồi thử lại. Vì an toàn, hồ sơ, chứng thư và
          dữ liệu tài khoản không được lưu ngoại tuyến trên thiết bị này.
        </p>
        <Link
          className="mt-7 inline-flex min-h-11 items-center rounded-lg bg-[#8b0000] px-5 font-semibold text-white"
          href="/"
        >
          Thử kết nối lại
        </Link>
      </section>
    </main>
  );
}
