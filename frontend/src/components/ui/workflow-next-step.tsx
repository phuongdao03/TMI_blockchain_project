import { ArrowRight, CheckCircle2 } from "lucide-react";
import Link from "next/link";

export function WorkflowNextStep({
  title,
  description,
  action,
  tone = "info",
}: {
  title: string;
  description: string;
  action?: { href: string; label: string };
  tone?: "info" | "success";
}) {
  const success = tone === "success";

  return (
    <section
      aria-live={success ? "polite" : undefined}
      className={`flex flex-col gap-4 rounded-xl border border-[var(--theme-border)] border-l-4 bg-[var(--theme-surface)] p-4 text-[var(--theme-text)] sm:flex-row sm:items-center sm:justify-between sm:p-5 ${success ? "border-l-emerald-600" : "border-l-[var(--theme-accent)]"}`}
      role={success ? "status" : undefined}
    >
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 shrink-0 text-[var(--theme-accent)]">
          {success ? (
            <CheckCircle2
              aria-hidden="true"
              className="size-5 text-emerald-700"
            />
          ) : (
            <ArrowRight aria-hidden="true" className="size-5" />
          )}
        </span>
        <div>
          <h2 className="font-bold leading-6">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
            {description}
          </p>
        </div>
      </div>
      {action ? (
        <Link
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 self-start rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] hover:text-[var(--theme-accent)] sm:self-auto"
          href={action.href}
        >
          {action.label}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      ) : null}
    </section>
  );
}
