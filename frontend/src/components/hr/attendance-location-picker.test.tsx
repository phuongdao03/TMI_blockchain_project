import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { AttendanceLocationPicker } from "@/components/hr/attendance-location-picker";

const mapSetView = vi.fn();
let mapEvents: {
  click?: (event: { latlng: { lat: number; lng: number } }) => void;
} = {};

vi.mock("react-leaflet", () => ({
  Circle: ({ radius }: { radius: number }) => (
    <div data-radius={radius} data-testid="attendance-geofence" />
  ),
  CircleMarker: () => <div data-testid="attendance-geofence-center" />,
  MapContainer: ({ children }: { children: ReactNode }) => (
    <div aria-label="Bản đồ cấu hình vùng chấm công" role="application">
      {children}
    </div>
  ),
  TileLayer: () => null,
  useMap: () => ({ setView: mapSetView }),
  useMapEvents: (events: typeof mapEvents) => {
    mapEvents = events;
    return { setView: mapSetView };
  },
}));

describe("AttendanceLocationPicker", () => {
  it("uses a map click to select the policy centre and updates the visible coordinates", () => {
    const onCoordinatesChange = vi.fn();
    const view = render(
      <AttendanceLocationPicker
        latitude=""
        longitude=""
        onCoordinatesChange={onCoordinatesChange}
        radiusMeters="180"
      />,
    );

    act(() => {
      mapEvents.click?.({ latlng: { lat: 1.3521234, lng: 103.8198456 } });
    });

    expect(onCoordinatesChange).toHaveBeenCalledWith("1.352123", "103.819846");
    view.rerender(
      <AttendanceLocationPicker
        latitude="1.352123"
        longitude="103.819846"
        onCoordinatesChange={onCoordinatesChange}
        radiusMeters="180"
      />,
    );
    expect(
      screen.getByTestId("attendance-geofence").getAttribute("data-radius"),
    ).toBe("180");
  });

  it("does not render a geofence until the policy has a valid centre", () => {
    render(
      <AttendanceLocationPicker
        latitude="not-a-coordinate"
        longitude="103.8198"
        onCoordinatesChange={vi.fn()}
        radiusMeters="180"
      />,
    );

    expect(screen.queryByTestId("attendance-geofence")).toBeNull();
  });

  it("moves to a city without changing the saved worksite coordinates", () => {
    const onCoordinatesChange = vi.fn();
    render(
      <AttendanceLocationPicker
        latitude=""
        longitude=""
        onCoordinatesChange={onCoordinatesChange}
        radiusMeters="250"
      />,
    );

    fireEvent.change(screen.getByLabelText("Đến thành phố"), {
      target: { value: "Singapore" },
    });

    expect(mapSetView).toHaveBeenCalledWith([1.3521, 103.8198], 12, {
      animate: false,
    });
    expect(onCoordinatesChange).not.toHaveBeenCalled();
    expect(screen.queryByTestId("attendance-geofence")).toBeNull();
  });
});
