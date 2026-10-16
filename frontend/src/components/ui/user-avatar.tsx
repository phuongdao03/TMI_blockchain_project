"use client";

import Image from "next/image";
import { UserRound } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

export function UserAvatar({
  displayName,
  size = 36,
  src,
  className,
}: {
  displayName?: string | null;
  size?: number;
  src?: string | null;
  className?: string;
}) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const [loadedSource, setLoadedSource] = useState<string | null>(null);
  const imageFailed = failedSource === src;
  const name = displayName?.trim() ?? "";

  return (
    <span
      aria-label={name ? `Ảnh đại diện của ${name}` : "Ảnh đại diện"}
      className={cn(
        "relative inline-grid shrink-0 place-items-center overflow-hidden rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] font-semibold text-[var(--theme-text)]",
        className,
      )}
      role="img"
      style={{ height: size, width: size, fontSize: Math.max(11, size * 0.34) }}
    >
      {name ? (
        <span aria-hidden="true">{getInitials(name)}</span>
      ) : (
        <UserRound aria-hidden="true" className="size-1/2" />
      )}
      {src && !imageFailed ? (
        <Image
          alt=""
          className={cn(
            "absolute inset-0 size-full object-cover",
            loadedSource === src ? "opacity-100" : "opacity-0",
          )}
          height={size}
          onError={() => setFailedSource(src)}
          onLoad={() => setLoadedSource(src)}
          sizes={`${size}px`}
          src={communityAvatarRenditionUrl(src, size)}
          unoptimized
          width={size}
        />
      ) : null}
    </span>
  );
}

function getInitials(name: string): string {
  const words = name.split(/\s+/).filter(Boolean);
  return words
    .slice(0, 2)
    .map((word) => Array.from(word)[0] ?? "")
    .join("")
    .toLocaleUpperCase("vi-VN");
}

function communityAvatarRenditionUrl(src: string, size: number): string {
  return /^\/api\/v1\/community\/avatars\/[0-9a-f-]{36}$/i.test(src)
    ? `${src}?width=${Math.min(256, Math.max(32, Math.ceil(size * 2)))}`
    : src;
}
