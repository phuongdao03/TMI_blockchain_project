import { describe, expect, it } from "vitest";

import {
  resolveMapTileConfig,
  resolveSatelliteTileConfig,
} from "@/lib/maps/tile-config";

describe("resolveMapTileConfig", () => {
  it("does not use volunteer OSM tiles as an implicit production provider", () => {
    expect(resolveMapTileConfig(undefined, undefined, true)).toBeNull();
    expect(
      resolveMapTileConfig(
        "https://tiles.example/{z}/{x}/{y}.png",
        undefined,
        true,
      ),
    ).toBeNull();
  });

  it("accepts a configured HTTPS tile provider with attribution", () => {
    expect(
      resolveMapTileConfig(
        "https://tiles.example/{z}/{x}/{y}.png",
        "Example Maps",
        true,
      ),
    ).toEqual({
      url: "https://tiles.example/{z}/{x}/{y}.png",
      attribution: expect.stringContaining("Example Maps"),
    });
  });

  it("rejects insecure or malformed tile templates", () => {
    expect(
      resolveMapTileConfig(
        "http://tiles.example/{z}/{x}/{y}.png",
        "Example Maps",
        true,
      ),
    ).toBeNull();
    expect(
      resolveMapTileConfig(
        "https://tiles.example/{z}/{x}.png",
        "Example Maps",
        true,
      ),
    ).toBeNull();
  });

  it("keeps the default volunteer tiles available for local development", () => {
    expect(resolveMapTileConfig(undefined, undefined, false)?.url).toContain(
      "tile.openstreetmap.org",
    );
  });
});

describe("resolveSatelliteTileConfig", () => {
  it("offers Stadia satellite imagery when the approved base map already uses Stadia", () => {
    expect(
      resolveSatelliteTileConfig(undefined, undefined, {
        url: "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}.png",
        attribution: "Stadia Maps",
      }),
    ).toMatchObject({
      url: "https://tiles.stadiamaps.com/tiles/alidade_satellite/{z}/{x}/{y}.jpg",
      attribution: expect.stringContaining("CNES"),
    });
  });

  it("keeps the configured query parameters when selecting satellite tiles", () => {
    expect(
      resolveSatelliteTileConfig(undefined, undefined, {
        url: "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}.png?api_key=example",
        attribution: "Stadia Maps",
      })?.url,
    ).toBe(
      "https://tiles.stadiamaps.com/tiles/alidade_satellite/{z}/{x}/{y}.jpg?api_key=example",
    );
  });

  it("does not assume a satellite provider for unrelated map tiles", () => {
    expect(
      resolveSatelliteTileConfig(undefined, undefined, {
        url: "https://tiles.example/{z}/{x}/{y}.png",
        attribution: "Example",
      }),
    ).toBeNull();
  });
});
