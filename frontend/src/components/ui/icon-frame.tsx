import type { LucideIcon } from "lucide-react";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type IconFrameSize = "sm" | "md" | "lg";
type IconFrameTone = "neutral" | "brand" | "inverse";

export function IconFrame({
  className,
  icon: Icon,
  size = "md",
  tone = "neutral",
  ...props
}: Omit<HTMLAttributes<HTMLSpanElement>, "children"> & {
  icon: LucideIcon;
  size?: IconFrameSize;
  tone?: IconFrameTone;
}) {
  return (
    <span
      className={cn(
        "ui-icon-frame",
        `ui-icon-frame--${size}`,
        `ui-icon-frame--${tone}`,
        className,
      )}
      {...props}
    >
      <Icon aria-hidden="true" focusable="false" strokeWidth={1.75} />
    </span>
  );
}
