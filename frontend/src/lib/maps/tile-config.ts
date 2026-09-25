const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

type MapTileConfig = { url: string; attribution: string };

export function resolveMapTileConfig(
  url: string | undefined,
  providerAttribution: string | undefined,
  isProduction: boolean,
): MapTileConfig | null {
  if (!url?.trim() || !providerAttribution?.trim()) {
    return isProduction
      ? null
      : {
          url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          attribution: OSM_ATTRIBUTION,
        };
  }
  const template = url.trim();
  if (
    !template.startsWith("https://") ||
    !["{z}", "{x}", "{y}"].every((part) => template.includes(part))
  ) {
    return null;
  }
  return {
    url: template,
    attribution: `${providerAttribution.trim()} | ${OSM_ATTRIBUTION}`,
  };
}

export const mapTileConfig = resolveMapTileConfig(
  process.env.NEXT_PUBLIC_OSM_TILE_URL,
  process.env.NEXT_PUBLIC_OSM_TILE_ATTRIBUTION,
  process.env.NODE_ENV === "production",
);
