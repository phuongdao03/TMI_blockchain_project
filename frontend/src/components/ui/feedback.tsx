import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

const tones = {
  error: {
    icon: AlertCircle,
    className: "ui-feedback--error",
  },
  info: {
    icon: Info,
    className: "ui-feedback--info",
  },
  success: {
    icon: CheckCircle2,
    className: "ui-feedback--success",
  },
  warning: {
    icon: TriangleAlert,
    className: "ui-feedback--warning",
  },
} as const;

export function Feedback({
  children,
  className,
  title,
  tone = "info",
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  children?: ReactNode;
  title: string;
  tone?: keyof typeof tones;
}) {
  const { className: toneClassName, icon: Icon } = tones[tone];
  return (
    <div
      className={cn(
        "ui-feedback grid grid-cols-[auto_1fr] gap-3 border-l-4 p-4",
        toneClassName,
        className,
      )}
      role={tone === "error" ? "alert" : "status"}
      {...props}
    >
      <Icon aria-hidden="true" className="mt-0.5 size-5" />
      <div>
        <p className="font-semibold">{title}</p>
        {children ? (
          <div className="mt-1 text-sm leading-6 opacity-80">{children}</div>
        ) : null}
      </div>
    </div>
  );
}
