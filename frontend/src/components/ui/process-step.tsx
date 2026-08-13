import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

export function ProcessStep({
  children,
  className,
  number,
  title,
  ...props
}: HTMLAttributes<HTMLElement> & {
  children: ReactNode;
  number: string;
  title: string;
}) {
  return (
    <article
      className={cn(
        "grid gap-4 border-t border-neutral-200 py-7 sm:grid-cols-[4rem_1fr]",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className="font-mono text-sm font-semibold tabular-nums text-primary-700"
      >
        {number}
      </span>
      <div>
        <h3 className="text-xl font-semibold tracking-tight text-neutral-950">
          {title}
        </h3>
        <div className="mt-3 text-sm leading-7 text-neutral-700">
          {children}
        </div>
      </div>
    </article>
  );
}
