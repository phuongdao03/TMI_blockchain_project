import Link from "next/link";

import type { CommunityRelatedWork } from "@/lib/api/types";

export function CommunityRelatedWorkLink({
  work,
}: {
  work: CommunityRelatedWork | null;
}) {
  if (!work) return null;

  return (
    <p className="mt-4 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 py-3 text-sm leading-6 text-[var(--theme-muted)]">
      <span className="font-semibold text-[var(--theme-text)]">
        Tác phẩm liên quan:{" "}
      </span>
      <Link
        aria-label={`Tác phẩm liên quan: ${work.title}`}
        className="font-bold text-[var(--theme-accent)] underline underline-offset-4 hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
        href={`/works/${encodeURIComponent(work.slug)}`}
      >
        {work.title}
      </Link>
    </p>
  );
}
