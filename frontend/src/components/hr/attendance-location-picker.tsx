"use client";

import "leaflet/dist/leaflet.css";

import type { LatLngExpression } from "leaflet";
import {
  Circle,
  CircleMarker,
  MapContainer,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { useEffect, useMemo, useState } from "react";

const DEFAULT_CENTER: [number, number] = [20, 0];
const CITY_LOCATIONS = [
  { name: "Hà Nội, Việt Nam", center: [21.0285, 105.8542] },
  { name: "TP. Hồ Chí Minh, Việt Nam", center: [10.8231, 106.6297] },
  { name: "Đà Nẵng, Việt Nam", center: [16.0544, 108.2022] },
  { name: "Singapore", center: [1.3521, 103.8198] },
  { name: "Bangkok, Thái Lan", center: [13.7563, 100.5018] },
  { name: "Tokyo, Nhật Bản", center: [35.6762, 139.6503] },
  { name: "London, Anh", center: [51.5072, -0.1276] },
  { name: "New York, Hoa Kỳ", center: [40.7128, -74.006] },
] satisfies { name: string; center: CoordinatePair }[];
const OSM_TILE_URL =
  process.env.NEXT_PUBLIC_OSM_TILE_URL ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

type CoordinatePair = [number, number];

function coordinate(value: string, minimum: number, maximum: number) {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= minimum && parsed <= maximum
    ? parsed
    : null;
}

function selectedCenter(
  latitude: string,
  longitude: string,
): CoordinatePair | null {
  const lat = coordinate(latitude, -90, 90);
  const lng = coordinate(longitude, -180, 180);
  return lat === null || lng === null ? null : [lat, lng];
}

function MapViewport({
  center,
  zoom,
}: {
  center: CoordinatePair;
  zoom: number;
}) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, zoom, { animate: false });
  }, [center, map, zoom]);

  return null;
}

function MapSelection({
  disabled,
  onCoordinatesChange,
}: {
  disabled: boolean;
  onCoordinatesChange: (latitude: string, longitude: string) => void;
}) {
  useMapEvents({
    click(event) {
      if (disabled) return;
      onCoordinatesChange(
        event.latlng.lat.toFixed(6),
        event.latlng.lng.toFixed(6),
      );
    },
  });
  return null;
}

export function AttendanceLocationPicker({
  disabled = false,
  latitude,
  longitude,
  onCoordinatesChange,
  radiusMeters,
}: {
  disabled?: boolean;
  latitude: string;
  longitude: string;
  onCoordinatesChange: (latitude: string, longitude: string) => void;
  radiusMeters: string;
}) {
  const center = useMemo(
    () => selectedCenter(latitude, longitude),
    [latitude, longitude],
  );
  const [cityName, setCityName] = useState("");
  const [mapDestination, setMapDestination] = useState<CoordinatePair | null>(
    null,
  );
  const radius = Number(radiusMeters);
  const hasRadius = Number.isFinite(radius) && radius > 0;
  const mapCenter: LatLngExpression =
    center ?? mapDestination ?? DEFAULT_CENTER;

  return (
    <section aria-labelledby="attendance-geofence-map-title" className="mt-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3
            className="text-sm font-bold text-neutral-950"
            id="attendance-geofence-map-title"
          >
            Bản đồ vùng chấm công
          </h3>
          <p className="mt-1 text-sm leading-6 text-neutral-600">
            Nhấp hoặc chạm vào bản đồ để đặt tâm vùng. Các trường tọa độ bên
            dưới vẫn có thể dùng để nhập giá trị đã được xác thực.
          </p>
        </div>
        <p
          aria-live="polite"
          className="rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 shadow-sm"
        >
          {center
            ? `Tâm vùng: ${center[0].toFixed(6)}, ${center[1].toFixed(6)}`
            : "Chưa chọn tâm vùng"}
        </p>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
        <label className="text-sm font-semibold text-neutral-800">
          Đến thành phố
          <select
            className="mt-1 min-h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm text-neutral-950"
            onChange={(event) => {
              const city = CITY_LOCATIONS.find(
                (item) => item.name === event.target.value,
              );
              setCityName(event.target.value);
              if (city) setMapDestination(city.center);
            }}
            value={cityName}
          >
            <option value="">Chọn thành phố để di chuyển bản đồ</option>
            {CITY_LOCATIONS.map((city) => (
              <option key={city.name} value={city.name}>
                {city.name}
              </option>
            ))}
          </select>
        </label>
        <p className="self-end text-xs leading-5 text-neutral-600">
          Chọn thành phố chỉ điều hướng bản đồ. Chạm đúng địa điểm làm việc để
          đặt tâm vùng.
        </p>
      </div>

      <div
        aria-label="Bản đồ cấu hình vùng chấm công"
        className="mt-3 overflow-hidden rounded-2xl border border-neutral-200 bg-neutral-100 shadow-inner"
        role="application"
      >
        <MapContainer
          center={mapCenter}
          className="h-72 w-full sm:h-96"
          minZoom={2}
          scrollWheelZoom
          zoom={center ? 16 : mapDestination ? 12 : 2}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url={OSM_TILE_URL}
          />
          <MapViewport
            center={center ?? mapDestination ?? DEFAULT_CENTER}
            zoom={center ? 16 : mapDestination ? 12 : 2}
          />
          <MapSelection
            disabled={disabled}
            onCoordinatesChange={onCoordinatesChange}
          />
          {center ? (
            <>
              <CircleMarker
                center={center}
                fillColor="#0f766e"
                fillOpacity={1}
                pathOptions={{ color: "#ffffff", weight: 3 }}
                radius={8}
              />
              {hasRadius ? (
                <Circle
                  center={center}
                  fillColor="#14b8a6"
                  fillOpacity={0.16}
                  pathOptions={{ color: "#0f766e", weight: 2 }}
                  radius={radius}
                />
              ) : null}
            </>
          ) : null}
        </MapContainer>
      </div>
      <p className="mt-3 text-xs leading-5 text-neutral-500">
        Bản đồ dùng dữ liệu OpenStreetMap. Chỉ Super Admin được cấu hình điểm
        làm việc; vị trí chấm công của nhân viên không được hiển thị tại đây.
      </p>
    </section>
  );
}
