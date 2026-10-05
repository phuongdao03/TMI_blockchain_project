import { LoaderCircle } from "lucide-react";

export function ImageLoadingStatus() {
  return (
    <div
      className="pointer-events-none absolute inset-0 grid place-items-center bg-[#1d0e0b]/75 text-white"
      role="status"
    >
      <span className="flex items-center gap-2 rounded-lg bg-black/65 px-4 py-3 text-sm font-semibold">
        <LoaderCircle
          aria-hidden="true"
          className="size-5 animate-spin motion-reduce:animate-none"
        />
        Đang tải hình ảnh…
      </span>
    </div>
  );
}
