import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <Link
      className={cn(
        "inline-flex min-h-11 items-center gap-3 rounded-lg font-bold text-neutral-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600",
        className,
      )}
      href="/"
    >
      <span className="grid size-14 shrink-0 place-items-center overflow-hidden">
        <Image
          alt="TMI Group"
          className="size-14 scale-[1.8] object-contain"
          height={64}
          loading="eager"
          src="/assets/brand/tmi-group-logo.png"
          width={64}
        />
      </span>
      <span>TMI Certificate</span>
    </Link>
  );
}
