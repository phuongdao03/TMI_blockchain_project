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

const STADIA_SATELLITE_ATTRIBUTION =
  '&copy; CNES, Distribution Airbus DS, &copy; Airbus DS, &copy; PlanetObserver (Contains Copernicus Data) | &copy; <a href="https://stadiamaps.com/attribution/">Stadia Maps</a> | &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> | ' + OSM_ATTRIBUTION;

export function resolveSatelliteTileConfig(
  url: string | undefined,
  attribution: string | undefined,
  base: MapTileConfig | null,
): MapTileConfig | null {
  if (url || attribution) return resolveMapTileConfig(url, attribution, true);
  if (!base) return null;
  try {
    const parsed = new URL(base.url);
    if (
      parsed.protocol !== "https:" ||
      !["tiles.stadiamaps.com", "tiles-eu.stadiamaps.com"].includes(parsed.hostname) ||
      !parsed.pathname.startsWith("/tiles/")
    ) return null;
    return {
      url: `https://${parsed.hostname}/tiles/alidade_satellite/{z}/{x}/{y}.jpg${parsed.search}`,
      attribution: STADIA_SATELLITE_ATTRIBUTION,
    };
  } catch {
    return null;
  }
}

export const satelliteTileConfig = resolveSatelliteTileConfig(
  process.env.NEXT_PUBLIC_SATELLITE_TILE_URL,
  process.env.NEXT_PUBLIC_SATELLITE_TILE_ATTRIBUTION,
  mapTileConfig,
);
