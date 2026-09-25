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

import { mapTileConfig } from "@/lib/maps/tile-config";

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
  const [tilesFailed, setTilesFailed] = useState(false);
  const [locationMessage, setLocationMessage] = useState("");
  const radius = Number(radiusMeters);
  const hasRadius = Number.isFinite(radius) && radius > 0;
  const mapCenter: LatLngExpression =
    mapDestination ?? center ?? DEFAULT_CENTER;

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

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          className="min-h-11 rounded-xl border border-primary-600 px-4 text-sm font-semibold text-primary-700 transition-colors hover:bg-primary-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50"
          disabled={disabled}
          onClick={() => {
            if (!navigator.geolocation) {
              setLocationMessage("Trình duyệt không hỗ trợ lấy vị trí. Nhập tọa độ trực tiếp ở bên dưới.");
              return;
            }
            setLocationMessage("Đang lấy vị trí thiết bị…");
            navigator.geolocation.getCurrentPosition(
              ({ coords }) => {
                onCoordinatesChange(coords.latitude.toFixed(6), coords.longitude.toFixed(6));
                setLocationMessage(`Đã lấy vị trí thiết bị (sai số khoảng ${Math.round(coords.accuracy)} m). Chỉ dùng khi bạn đang ở văn phòng.`);
              },
              () => setLocationMessage("Không thể lấy vị trí. Hãy cho phép định vị qua HTTPS hoặc nhập tọa độ trực tiếp."),
              { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
            );
          }}
          type="button"
        >
          Lấy vị trí thiết bị tại văn phòng
        </button>
        <button
          className="min-h-11 rounded-xl px-3 text-sm font-medium text-neutral-700 underline underline-offset-4 hover:text-neutral-950"
          onClick={() => setTilesFailed(true)}
          type="button"
        >
          Bản đồ không hiển thị
        </button>
      </div>
      {locationMessage ? <p aria-live="polite" className="mt-2 text-sm text-neutral-700">{locationMessage}</p> : null}

      <div className="mt-4 grid min-w-0 gap-2">
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
        {center && mapDestination ? (
          <button
            className="min-h-11 justify-self-start rounded-xl border border-neutral-300 bg-white px-3 text-sm font-semibold text-neutral-800 transition-colors hover:border-primary-600 hover:text-primary-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
            onClick={() => {
              setCityName("");
              setMapDestination(null);
            }}
            type="button"
          >
            Về điểm chấm công đã lưu
          </button>
        ) : null}
        <p className="text-xs leading-5 text-neutral-600">
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
          zoom={mapDestination ? 12 : center ? 16 : 2}
        >
          {!tilesFailed && mapTileConfig ? (
            <TileLayer
              attribution={mapTileConfig.attribution}
              eventHandlers={{ tileerror: () => setTilesFailed(true) }}
              url={mapTileConfig.url}
            />
          ) : null}
          <MapViewport
            center={mapDestination ?? center ?? DEFAULT_CENTER}
            zoom={mapDestination ? 12 : center ? 16 : 2}
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
      {tilesFailed || !mapTileConfig ? (
        <p className="mt-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950" role="status">
          Bản đồ nền tạm thời không tải được. Nhập tọa độ trực tiếp ở bên dưới hoặc lấy vị trí thiết bị khi đang ở văn phòng; vùng chấm công vẫn được lưu chính xác.
        </p>
      ) : null}
      <p className="mt-3 text-xs leading-5 text-neutral-500">
        Bản đồ dùng dữ liệu OpenStreetMap. Chỉ Super Admin được cấu hình điểm
        làm việc; vị trí chấm công của nhân viên không được hiển thị tại đây.
      </p>
    </section>
  );
}
