import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

type WorkspacePageHeaderProps = {
  section: string;
  title: string;
  description: string;
  id?: string;
  icon?: LucideIcon;
  action?: ReactNode;
};

export function WorkspacePageHeader({
  section,
  title,
  description,
  id,
  icon: Icon,
  action,
}: WorkspacePageHeaderProps) {
  return (
    <header className="flex flex-col gap-4 border-b border-[var(--theme-border)] pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-xs font-semibold tracking-[0.14em] text-[var(--theme-accent)] uppercase">
          {Icon ? <Icon aria-hidden="true" className="size-4" /> : null}
          {section}
        </p>
        <h1
          className="mt-2 text-3xl leading-tight font-bold tracking-tight text-[var(--theme-text)] sm:text-4xl"
          id={id}
        >
          {title}
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--theme-muted)] sm:text-base">
          {description}
        </p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}
