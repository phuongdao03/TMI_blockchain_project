import { ArrowLeft, SearchX } from "lucide-react";
import Link from "next/link";

export default function PublicWorkNotFound() {
  return (
    <main className="mx-auto grid min-h-[70dvh] max-w-xl place-items-center px-4 text-center">
      <div>
        <SearchX className="mx-auto size-10 text-gold-300" />
        <h1 className="mt-5 text-3xl font-bold text-white">
          Không tìm thấy tác phẩm
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Liên kết có thể không còn công khai hoặc đã được thay đổi.
        </p>
        <Link
          className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 px-5 text-sm font-bold text-white"
          href="/thu-vien"
        >
          <ArrowLeft className="size-4" /> Về catalog
        </Link>
      </div>
    </main>
  );
}
