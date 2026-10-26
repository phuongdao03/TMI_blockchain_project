import { Megaphone } from "lucide-react";

import type { AdvertisingPlacement } from "@/lib/api/types";

type PreviewLayout =
  | "featured-dossier"
  | "homepage-spotlight"
  | "community-banner"
  | "homepage-hero"
  | "generic";

const placementLayouts: Record<string, PreviewLayout> = {
  FEATURED_DOSSIER: "featured-dossier",
  HOMEPAGE_SPOTLIGHT: "homepage-spotlight",
  COMMUNITY_BANNER: "community-banner",
  HOMEPAGE_HERO: "homepage-hero",
};

function getPreviewLayout(code: string): PreviewLayout {
  return placementLayouts[code] ?? "generic";
}

function Placeholder({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`block rounded-full bg-[var(--theme-border)]/70 ${className}`}
    />
  );
}

function PlacementSlot({
  className,
  placement,
}: {
  className?: string;
  placement: AdvertisingPlacement;
}) {
  return (
    <div
      aria-label={`Vị trí quảng cáo đã chọn: ${placement.name}`}
      aria-live="polite"
      className={`flex min-h-24 flex-col justify-center gap-2 rounded-lg border-2 border-dashed border-primary-700 bg-primary-50 p-3 text-primary-950 sm:p-4 ${className ?? ""}`}
      role="group"
    >
      <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.08em]">
        <Megaphone aria-hidden="true" className="size-4 shrink-0" />
        Vị trí quảng cáo đã chọn
      </span>
      <span className="font-semibold leading-5">{placement.name}</span>
      <span className="text-xs font-medium">{placement.pageLocation}</span>
    </div>
  );
}

function ContentPlaceholder({ count = 3 }: { count?: number }) {
  return (
    <div
      aria-hidden="true"
      className={`grid gap-2 ${count > 1 ? "sm:grid-cols-3" : "grid-cols-1"}`}
    >
      {Array.from({ length: count }, (_, index) => (
        <div
          className="space-y-2 rounded-lg border border-[var(--theme-border)] p-2.5"
          key={index}
        >
          <Placeholder className="h-12 w-full rounded-md" />
          <Placeholder className="h-2.5 w-4/5" />
          <Placeholder className="h-2.5 w-3/5" />
        </div>
      ))}
    </div>
  );
}

function PageHeading({ label }: { label?: string }) {
  return (
    <div aria-hidden="true" className="space-y-2">
      {label ? (
        <span className="text-xs font-semibold text-[var(--theme-muted)]">
          {label}
        </span>
      ) : null}
      <Placeholder className="h-3 w-1/3" />
      <Placeholder className="h-2.5 w-2/3" />
    </div>
  );
}

function PlacementWireframe({
  layout,
  placement,
}: {
  layout: PreviewLayout;
  placement: AdvertisingPlacement;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
      <div
        aria-hidden="true"
        className="flex items-center gap-2 border-b border-[var(--theme-border)] px-3 py-2"
      >
        <span className="size-2 rounded-full bg-[var(--theme-muted)]/50" />
        <span className="size-2 rounded-full bg-[var(--theme-muted)]/50" />
        <span className="size-2 rounded-full bg-[var(--theme-muted)]/50" />
        <Placeholder className="ml-2 h-2.5 w-28" />
      </div>

      <div className="space-y-3 p-3 sm:p-4">
        <div
          aria-hidden="true"
          className="flex items-center justify-between border-b border-[var(--theme-border)] pb-3"
        >
          <Placeholder className="h-3 w-20" />
          <div className="flex gap-2">
            <Placeholder className="h-2.5 w-10" />
            <Placeholder className="h-2.5 w-10" />
            <Placeholder className="h-2.5 w-10" />
          </div>
        </div>

        {layout === "homepage-hero" ? (
          <PlacementSlot className="min-h-28" placement={placement} />
        ) : null}

        {layout === "community-banner" ? (
          <>
            <PageHeading label="Cộng đồng" />
            <PlacementSlot className="min-h-20" placement={placement} />
            <ContentPlaceholder />
          </>
        ) : null}

        {layout === "featured-dossier" ? (
          <>
            <PageHeading label="Hồ sơ đề cử" />
            <div className="grid gap-2 sm:grid-cols-3">
              <PlacementSlot className="min-h-32" placement={placement} />
              <div className="hidden sm:block">
                <ContentPlaceholder count={1} />
              </div>
              <div className="hidden sm:block">
                <ContentPlaceholder count={1} />
              </div>
            </div>
          </>
        ) : null}

        {layout === "homepage-spotlight" ? (
          <>
            <div
              aria-hidden="true"
              className="h-16 rounded-lg bg-[var(--theme-border)]/40 sm:h-20"
            />
            <PlacementSlot className="min-h-24" placement={placement} />
            <ContentPlaceholder />
          </>
        ) : null}

        {layout === "generic" ? (
          <>
            <PageHeading />
            <PlacementSlot className="min-h-24" placement={placement} />
            <ContentPlaceholder />
          </>
        ) : null}
      </div>
    </div>
  );
}

export function AdvertisingPlacementPreview({
  placement,
}: {
  placement: AdvertisingPlacement;
}) {
  const layout = getPreviewLayout(placement.code);

  return (
    <section
      aria-label="Bản xem trước vị trí quảng cáo"
      className="space-y-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 sm:p-4"
      data-placement-layout={layout}
      role="region"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-[var(--theme-text)]">
            Vị trí trên trang
          </h3>
          <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
            {layout === "generic"
              ? "Mô phỏng tổng quát cho vị trí tùy chỉnh."
              : "Mô phỏng minh họa vị trí quảng cáo trên trang."}
          </p>
        </div>
        <span className="rounded-full border border-[var(--theme-border)] px-2.5 py-1 text-xs font-semibold text-[var(--theme-muted)]">
          Bản minh họa
        </span>
      </div>
      <PlacementWireframe layout={layout} placement={placement} />
      <p className="text-xs leading-5 text-[var(--theme-muted)]">
        Đây là khung mô phỏng để bạn hình dung vị trí; giao diện thực tế có thể
        thay đổi theo trang và thiết bị.
      </p>
    </section>
  );
}
