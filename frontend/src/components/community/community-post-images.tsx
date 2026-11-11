"use client";

import { useRef, useState } from "react";
import Image from "next/image";

import type { CommunityPostImage } from "@/lib/api/community-types";

export function CommunityPostImages({
  images,
  postSlug,
  postTitle,
  priority = false,
  presentation = "detail",
}: {
  images: readonly CommunityPostImage[];
  postSlug: string;
  postTitle: string;
  priority?: boolean;
  presentation?: "detail" | "feed";
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
      {presentation === "detail" ? (
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
      ) : null}
      <ul
        aria-label="Ảnh đính kèm bài viết"
        className={
          presentation === "feed"
            ? "mt-0 grid grid-cols-2 gap-1"
            : "mt-5 grid grid-cols-1 gap-3 sm:gap-4"
        }
      >
        {safeImages.map((image, index) => (
          <li
            className={
              presentation === "feed"
                ? `overflow-hidden bg-[var(--theme-bg)] ${safeImages.length === 1 || index === 0 ? "col-span-2 aspect-[16/9]" : "aspect-square"}`
                : "overflow-hidden rounded-xl bg-[var(--theme-elevated)]"
            }
            key={image.id}
          >
            <button
              type="button"
              className={
                presentation === "feed"
                  ? "group block h-full w-full cursor-zoom-in focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                  : "block w-full cursor-zoom-in focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
              }
              aria-label={`Xem lớn ảnh ${index + 1}`}
              onClick={() => {
                setSelected(index);
                dialog.current?.showModal();
              }}
            >
              <Image
                alt={`${postTitle} — ảnh đính kèm ${index + 1}`}
                className={
                  presentation === "feed"
                    ? "h-full w-full object-cover transition-transform duration-200 motion-safe:group-hover:scale-[1.02] motion-reduce:transition-none"
                    : imageSize === "compact"
                      ? "max-h-80 w-full object-contain"
                      : "h-auto w-full object-contain"
                }
                width={960}
                height={720}
                loading={priority && index === 0 ? "eager" : "lazy"}
                fetchPriority={priority && index === 0 ? "high" : "auto"}
                sizes={
                  presentation === "feed"
                    ? "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                    : "(max-width: 768px) 100vw, 768px"
                }
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
        <div className="mb-3 flex justify-end">
          <button
            className="min-h-11 rounded-lg border px-4"
            autoFocus
            type="button"
            onClick={() => dialog.current?.close()}
          >
            Đóng ảnh
          </button>
        </div>
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
