import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

const tones = {
  error: {
    icon: AlertCircle,
    className: "border-red-200 bg-red-50 text-red-950",
  },
  info: {
    icon: Info,
    className: "border-slate-200 bg-slate-50 text-slate-950",
  },
  success: {
    icon: CheckCircle2,
    className: "border-emerald-200 bg-emerald-50 text-emerald-950",
  },
  warning: {
    icon: TriangleAlert,
    className: "border-amber-200 bg-amber-50 text-amber-950",
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
        "grid grid-cols-[auto_1fr] gap-3 border-l-4 p-4",
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
