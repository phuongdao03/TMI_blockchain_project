import Link from "next/link";
import type { useDossierPreparation } from "./use-dossier-preparation";

export function PreparationRecoveryNotice({
  recovery,
}: {
  recovery: ReturnType<typeof useDossierPreparation>;
}) {
  if (recovery.conflict)
    return (
      <section
        className="rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"
        role="alert"
      >
        <h2 className="font-bold">Có thay đổi từ thiết bị hoặc tab khác</h2>
        <p className="mt-2 text-sm">
          Nội dung bạn đang nhập vẫn được giữ. Chọn bản muốn tiếp tục trước khi
          lưu hoặc tạo nháp.
        </p>
        <p className="mt-2 break-words text-sm">
          {recovery.conflict.payload
            ? `Bản trên tài khoản: ${recovery.conflict.payload.values.title || "Chưa có tên hồ sơ"}`
            : "Tài khoản không còn dữ liệu chuẩn bị này; nếu đã tạo nháp, hãy kiểm tra Hồ sơ của tôi."}
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-sm font-bold">
          <button
            type="button"
            className="min-h-11 underline"
            onClick={recovery.keepLocal}
          >
            Giữ bản đang nhập
          </button>
          <button
            type="button"
            className="min-h-11 underline"
            onClick={recovery.useServer}
          >
            Dùng bản trên tài khoản
          </button>
          <Link
            className="inline-flex min-h-11 items-center underline"
            href="/dossiers"
          >
            Hồ sơ của tôi
          </Link>
        </div>
      </section>
    );
  return (
    <div className="rounded-lg border border-[var(--theme-border)] px-4 py-3 text-sm text-[var(--theme-muted)]">
      <p role="status" aria-live="polite">
        {recovery.saving
          ? "Đang lưu lên tài khoản…"
          : recovery.dirty
            ? "Chưa đồng bộ hết thay đổi."
            : recovery.revision
              ? "Đã lưu dữ liệu chuẩn bị trên tài khoản."
              : "Dữ liệu chuẩn bị sẽ tự động lưu theo tài khoản."}
      </p>
      {recovery.recovered ? (
        <p className="mt-1">
          Đã khôi phục nội dung đang chuẩn bị để bạn tiếp tục.
        </p>
      ) : null}
      {recovery.error ? (
        <div className="mt-2" role="alert">
          <p>{recovery.error}</p>
          <button
            className="min-h-11 font-bold underline"
            type="button"
            onClick={() => void recovery.flush()}
          >
            Thử lưu lại
          </button>
        </div>
      ) : null}
      {recovery.storageError ? (
        <p className="mt-2">
          Trình duyệt chưa lưu được bản khôi phục tạm. Hãy chờ đồng bộ trên tài
          khoản trước khi đóng trang.
        </p>
      ) : null}
    </div>
  );
}
