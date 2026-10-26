"use client";

import { useRef, useState } from "react";
import Image from "next/image";

import type { CommunityPostImage } from "@/lib/api/types";

export function CommunityPostImages({
  images,
  postSlug,
  postTitle,
  priority = false,
}: {
  images: readonly CommunityPostImage[];
  postSlug: string;
  postTitle: string;
  priority?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState(0);
  const [imageSize, setImageSize] = useState("full");
  const safeImages = images.filter((image) =>
    isCommunityAttachmentUrl(image, postSlug),
  );
  const expandedImage = safeImages[selected] ?? safeImages[0];
  if (!expandedImage) return null;

  return (
    <>
      <label className="mt-4 flex items-center gap-3 text-sm">
        Kích thước hiển thị ảnh
        <select
          aria-label="Kích thước hiển thị ảnh"
          value={imageSize}
          onChange={(event) => setImageSize(event.target.value)}
          className="rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-2"
        >
          <option value="full">Đầy đủ ảnh</option>
          <option value="compact">Thu gọn</option>
        </select>
      </label>
      <ul
        aria-label="Ảnh đính kèm bài viết"
        className="mt-5 grid grid-cols-1 gap-3 sm:gap-4"
      >
        {safeImages.map((image, index) => (
          <li
            className="overflow-hidden rounded-xl bg-[var(--theme-elevated)]"
            key={image.id}
          >
            <button
              type="button"
              className="block w-full cursor-zoom-in"
              aria-label={`Xem lớn ảnh ${index + 1}`}
              onClick={() => {
                setSelected(index);
                dialog.current?.showModal();
              }}
            >
              <Image
                alt={`${postTitle} — ảnh đính kèm ${index + 1}`}
                className={
                  imageSize === "compact"
                    ? "max-h-80 w-full object-contain"
                    : "h-auto w-full object-contain"
                }
                width={960}
                height={720}
                loading={priority && index === 0 ? "eager" : "lazy"}
                fetchPriority={priority && index === 0 ? "high" : "auto"}
                sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 640px"
                src={`${image.url}?width=960`}
                unoptimized
              />
            </button>
          </li>
        ))}
      </ul>
      <dialog
        ref={dialog}
        aria-label="Xem ảnh bài viết"
        className="m-auto max-h-[95dvh] w-[min(96vw,1440px)] bg-[var(--theme-surface)] p-4 text-[var(--theme-text)] backdrop:bg-black/80"
        onClick={(event) => {
          if (event.target === event.currentTarget) dialog.current?.close();
        }}
      >
        <form method="dialog" className="mb-3 flex justify-end">
          <button className="min-h-11 rounded-lg border px-4" autoFocus>
            Đóng ảnh
          </button>
        </form>
        <Image
          alt={`${postTitle} — ảnh ${selected + 1}`}
          src={`${expandedImage.url}?width=1600`}
          width={1600}
          height={1200}
          className="max-h-[80dvh] w-full object-contain"
          unoptimized
        />
      </dialog>
    </>
  );
}

function isCommunityAttachmentUrl(
  image: CommunityPostImage,
  postSlug: string,
): boolean {
  const expectedPath = `/api/v1/community/posts/${encodeURIComponent(postSlug)}/media/${encodeURIComponent(image.id)}`;
  if (image.url !== expectedPath) return false;

  try {
    const parsed = new URL(image.url, "https://app.invalid");
    return (
      parsed.origin === "https://app.invalid" &&
      parsed.pathname === expectedPath &&
      !parsed.search &&
      !parsed.hash
    );
  } catch {
    return false;
  }
}
