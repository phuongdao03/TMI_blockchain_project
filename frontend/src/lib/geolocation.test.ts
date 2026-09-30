import { afterEach, describe, expect, it, vi } from "vitest";

import { captureForegroundLocation } from "@/lib/geolocation";

const originalSecureContext = Object.getOwnPropertyDescriptor(
  window,
  "isSecureContext",
);

function enableSecureLocation(
  getCurrentPosition: Geolocation["getCurrentPosition"],
) {
  Object.defineProperty(window, "isSecureContext", {
    configurable: true,
    value: true,
  });
  vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
}

afterEach(() => {
  vi.unstubAllGlobals();
  if (originalSecureContext) {
    Object.defineProperty(window, "isSecureContext", originalSecureContext);
  } else {
    Reflect.deleteProperty(window, "isSecureContext");
  }
});

describe("captureForegroundLocation", () => {
  it("requests one fresh high-accuracy location after the attendance action", async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) => {
      success({
        coords: {
          accuracy: 18.5,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          latitude: 10.7769,
          longitude: 106.7009,
          speed: null,
          toJSON: () => ({}),
        },
        timestamp: Date.parse("2026-09-21T02:30:00.000Z"),
        toJSON: () => ({}),
      });
    });
    enableSecureLocation(getCurrentPosition);

    await expect(captureForegroundLocation()).resolves.toEqual({
      latitude: 10.7769,
      longitude: 106.7009,
      accuracyMeters: 18.5,
      clientCapturedAt: "2026-09-21T02:30:00.000Z",
    });
    expect(getCurrentPosition).toHaveBeenCalledWith(
      expect.any(Function),
      expect.any(Function),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15_000 },
    );
  });

  it("explains a denied permission without exposing position details", async () => {
    const deniedError: GeolocationPositionError = {
      code: 1,
      message: "browser-specific detail",
      PERMISSION_DENIED: 1,
      POSITION_UNAVAILABLE: 2,
      TIMEOUT: 3,
    };
    const getCurrentPosition = vi.fn(
      (_success: PositionCallback, error: PositionErrorCallback) => {
        error(deniedError);
      },
    );
    enableSecureLocation(getCurrentPosition);

    await expect(captureForegroundLocation()).rejects.toThrow(
      "Chưa được cấp quyền vị trí cho lần lấy này.",
    );
  });

  it("retries with standard accuracy when precise GPS times out", async () => {
    const getCurrentPosition = vi.fn(
      (
        success: PositionCallback,
        error: PositionErrorCallback,
        options: PositionOptions,
      ) => {
        if (options.enableHighAccuracy) {
          error({
            code: 3,
            message: "timeout",
            PERMISSION_DENIED: 1,
            POSITION_UNAVAILABLE: 2,
            TIMEOUT: 3,
          });
          return;
        }
        success({
          coords: {
            latitude: 10.72,
            longitude: 106.7,
            accuracy: 85,
          } as GeolocationCoordinates,
          timestamp: Date.parse("2026-09-30T02:00:00Z"),
        } as GeolocationPosition);
      },
    );
    enableSecureLocation(getCurrentPosition);
    await expect(captureForegroundLocation()).resolves.toMatchObject({
      latitude: 10.72,
      longitude: 106.7,
      accuracyMeters: 85,
    });
    expect(getCurrentPosition).toHaveBeenCalledTimes(2);
    expect(getCurrentPosition).toHaveBeenLastCalledWith(
      expect.any(Function),
      expect.any(Function),
      { enableHighAccuracy: false, maximumAge: 0, timeout: 15_000 },
    );
  });

  it("requires a secure browser context before requesting device location", async () => {
    const getCurrentPosition = vi.fn();
    Object.defineProperty(window, "isSecureContext", {
      configurable: true,
      value: false,
    });
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });

    await expect(captureForegroundLocation()).rejects.toThrow("HTTPS");
    expect(getCurrentPosition).not.toHaveBeenCalled();
  });
});
