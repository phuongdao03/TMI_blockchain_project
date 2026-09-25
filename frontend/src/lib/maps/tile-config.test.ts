import { describe, expect, it } from "vitest";

import { resolveMapTileConfig } from "@/lib/maps/tile-config";

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
