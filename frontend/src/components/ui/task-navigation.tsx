"use client";

export function TaskNavigation<T extends string>({
  label,
  items,
  value,
  onChange,
}: {
  label: string;
  items: readonly { id: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <nav
      aria-label={label}
      className="flex min-w-0 flex-wrap gap-1 border-b border-[var(--theme-border)] py-2"
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          aria-pressed={value === item.id}
          onClick={() => onChange(item.id)}
          className={`min-h-11 rounded-md px-3 py-2 text-left text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] ${value === item.id ? "bg-[var(--theme-elevated)] text-[var(--theme-accent)]" : "text-[var(--theme-muted)] hover:text-[var(--theme-text)]"}`}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
