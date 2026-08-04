export type PublicCatalogEvent =
  | {
      name: "catalog_filter_applied";
      properties: { activeFilterCount: number; sort: string };
    }
  | {
      name: "catalog_work_opened";
      properties: {
        slug: string;
        position: number;
        source: "featured" | "list";
      };
    }
  | {
      name: "catalog_page_changed";
      properties: { page: number };
    };

export const PUBLIC_CATALOG_ANALYTICS_EVENT = "tmi:public-catalog";

export function trackPublicCatalog(event: PublicCatalogEvent): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<PublicCatalogEvent>(PUBLIC_CATALOG_ANALYTICS_EVENT, {
      detail: event,
    }),
  );
}
