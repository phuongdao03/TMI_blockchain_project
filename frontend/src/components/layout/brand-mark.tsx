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
      <span className="grid size-11 shrink-0 place-items-center overflow-hidden sm:size-14">
        <Image
          alt="TMI Group"
          className="size-11 scale-[1.8] object-contain sm:size-14"
          height={64}
          loading="eager"
          src="/assets/brand/tmi-group-logo.png"
          width={64}
        />
      </span>
      <span className="hidden leading-none min-[390px]:grid">
        <strong className="text-sm tracking-[-0.02em] sm:text-base">
          Đề cử Tinh Hoa Việt
        </strong>
        <small className="brand-subtitle mt-1 text-[0.55rem] font-semibold tracking-[0.16em] uppercase">
          TMI Group
        </small>
      </span>
    </Link>
  );
}
