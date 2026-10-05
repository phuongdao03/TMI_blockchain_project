import { LoaderCircle } from "lucide-react";

export function AuthNavigationStatus() {
  return (
    <div
      className="fixed inset-0 z-[100] grid place-items-center bg-[#140b0b]/90 px-6 backdrop-blur-sm"
      role="status"
    >
      <div className="w-full max-w-sm rounded-xl border border-[#ad8883]/35 bg-[#211313] px-8 py-9 text-center text-[#f6e9df] shadow-2xl">
        <LoaderCircle
          aria-hidden="true"
          className="auth-activity-spinner mx-auto size-9 text-[#e8bb74]"
        />
        <p className="mt-5 text-lg font-semibold">
          Đang mở không gian làm việc…
        </p>
        <p className="mt-2 text-sm text-[#cbbab3]">
          Phiên đăng nhập đã sẵn sàng. Vui lòng chờ trong giây lát.
        </p>
      </div>
    </div>
  );
}
