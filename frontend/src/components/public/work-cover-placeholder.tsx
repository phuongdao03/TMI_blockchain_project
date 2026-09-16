import { FileText, ImageIcon, Music2, Video } from "lucide-react";

export function WorkCoverPlaceholder({
  title,
  label,
  kind = "DOCUMENT",
}: {
  title: string;
  label: string;
  kind?: string;
}) {
  const Icon =
    kind === "AUDIO"
      ? Music2
      : kind === "VIDEO"
        ? Video
        : kind === "IMAGE"
          ? ImageIcon
          : FileText;
  return (
    <div
      className="flex aspect-video w-full flex-col justify-between bg-[var(--thv-red-dark)] p-5 text-[var(--thv-white)] sm:p-7"
      aria-label={`Bìa mặc định: ${title}`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-bold tracking-wider uppercase">
          {label}
        </span>
        <Icon
          aria-hidden="true"
          className="size-6 shrink-0 text-[var(--thv-gold)]"
        />
      </div>
      <p className="line-clamp-3 text-xl leading-tight font-bold break-words sm:text-2xl">
        {title}
      </p>
      <span className="text-xs opacity-75">
        Tinh Hoa Việt · Ảnh đại diện đang cập nhật
      </span>
    </div>
  );
}
