import { LoaderCircle } from "lucide-react";

export function PageLoading() {
  return (
    <section className="page-loading" role="status">
      <span className="page-loading__message">
        <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
        Đang tải nội dung…
      </span>
      <div aria-hidden="true" className="page-loading__placeholder">
        <div className="page-loading__shape page-loading__eyebrow" />
        <div className="page-loading__shape page-loading__title" />
        <div className="page-loading__shape page-loading__summary" />
        <div className="page-loading__cards">
          <div className="page-loading__shape page-loading__card" />
          <div className="page-loading__shape page-loading__card" />
          <div className="page-loading__shape page-loading__card" />
        </div>
      </div>
    </section>
  );
}
