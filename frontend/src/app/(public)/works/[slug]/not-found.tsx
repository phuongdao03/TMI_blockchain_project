import { ArrowLeft, SearchX } from "lucide-react";
import Link from "next/link";

export default function PublicWorkNotFound() {
  return (
    <main className="public-status-layout">
      <section
        aria-labelledby="work-not-found-title"
        className="public-status-panel"
        role="status"
      >
        <SearchX
          aria-hidden="true"
          className="public-status-panel__icon mx-auto size-10"
        />
        <h1
          className="public-status-panel__title mt-5 text-3xl font-bold"
          id="work-not-found-title"
        >
          Không tìm thấy đề cử
        </h1>
        <p className="public-status-panel__copy mt-3 text-sm leading-6">
          Liên kết có thể không còn công khai hoặc đã được thay đổi.
        </p>
        <Link
          className="public-status-panel__action mt-6 inline-flex min-h-11 gap-2 px-5 text-sm font-bold"
          href="/works"
        >
          <ArrowLeft className="size-4" /> Về danh sách đề cử
        </Link>
      </section>
    </main>
  );
}
