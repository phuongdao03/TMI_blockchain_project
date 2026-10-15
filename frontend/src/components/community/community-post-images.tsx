import Image from "next/image";

import type { CommunityPostImage } from "@/lib/api/types";

export function CommunityPostImages({
  images,
  postSlug,
  postTitle,
}: {
  images: readonly CommunityPostImage[];
  postSlug: string;
  postTitle: string;
}) {
  const safeImages = images.filter((image) =>
    isCommunityAttachmentUrl(image, postSlug),
  );
  if (!safeImages.length) return null;

  return (
    <ul
      aria-label="Ảnh đính kèm bài viết"
      className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4"
    >
      {safeImages.map((image, index) => (
        <li
          className="relative aspect-[4/3] overflow-hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)]"
          key={image.id}
        >
          <Image
            alt={`${postTitle} — ảnh đính kèm ${index + 1}`}
            className="object-cover"
            fill
            loading="lazy"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 640px"
            src={image.url}
            unoptimized
          />
        </li>
      ))}
    </ul>
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
