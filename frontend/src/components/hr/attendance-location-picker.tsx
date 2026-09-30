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

import { hrAttendanceConfigurationApi } from "@/lib/api/client";
import {
  captureForegroundLocation,
  LocationCaptureError,
} from "@/lib/geolocation";
import { mapTileConfig, satelliteTileConfig } from "@/lib/maps/tile-config";

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
  const [cityResults, setCityResults] = useState<
    { name: string; center: CoordinatePair }[]
  >([]);
  const [cityMessage, setCityMessage] = useState("");
  const [searchingCity, setSearchingCity] = useState(false);
  const [mapDestination, setMapDestination] = useState<CoordinatePair | null>(
    null,
  );
  const [destinationZoom, setDestinationZoom] = useState(12);
  const [addressQuery, setAddressQuery] = useState("");
  const [addressResults, setAddressResults] = useState<
    { label: string; latitude: number; longitude: number }[]
  >([]);
  const [selectedAddress, setSelectedAddress] = useState<string | null>(null);
  const [addressMessage, setAddressMessage] = useState("");
  const [searchingAddress, setSearchingAddress] = useState(false);
  const [tilesFailed, setTilesFailed] = useState(false);
  const [tileAttempt, setTileAttempt] = useState(0);
  const [mapStyle, setMapStyle] = useState<"street" | "satellite">("street");
  const [locationMessage, setLocationMessage] = useState("");
  const [capturingLocation, setCapturingLocation] = useState(false);
  const radius = Number(radiusMeters);
  const hasRadius = Number.isFinite(radius) && radius > 0;
  const mapCenter: LatLngExpression =
    mapDestination ?? center ?? DEFAULT_CENTER;
  const activeTiles = mapStyle === "satellite" ? satelliteTileConfig : mapTileConfig;

  function goToCity(city: { name: string; center: CoordinatePair }) {
    setCityName(city.name);
    setMapDestination(city.center);
    setDestinationZoom(12);
    setSelectedAddress(null);
    setCityResults([]);
    setCityMessage("Đã chuyển bản đồ. Chạm vào đúng địa điểm để đặt tâm vùng.");
  }

  async function searchCity() {
    const query = cityName.trim();
    if (query.length < 2) {
      setCityMessage("Nhập ít nhất 2 ký tự để tìm thành phố.");
      return;
    }
    const local = CITY_LOCATIONS.filter((city) =>
      city.name.toLocaleLowerCase("vi").includes(query.toLocaleLowerCase("vi")),
    );
    if (local.length > 0) {
      setCityResults(local);
      setCityMessage("");
      return;
    }
    setSearchingCity(true);
    try {
      const results = await hrAttendanceConfigurationApi.searchAddress(query);
      setCityResults(results.map((result) => ({
        name: result.label,
        center: [result.latitude, result.longitude],
      })));
      setCityMessage(results.length ? "Chọn một kết quả để chuyển bản đồ." : "Không tìm thấy địa điểm. Thử tên thành phố kèm quốc gia.");
    } catch {
      setCityMessage("Không tìm được thành phố lúc này. Thử lại hoặc tìm địa chỉ bên dưới.");
    } finally {
      setSearchingCity(false);
    }
  }

  async function searchAddress() {
    const query = addressQuery.trim();
    if (query.length < 3) {
      setAddressMessage("Nhập ít nhất 3 ký tự trong địa chỉ cần tìm.");
      return;
    }
    setSearchingAddress(true);
    setAddressMessage("");
    setAddressResults([]);
    try {
      const results = await hrAttendanceConfigurationApi.searchAddress(query);
      setAddressResults(results);
      if (results.length === 0) {
        setAddressMessage(
          "Không tìm thấy địa chỉ phù hợp. Hãy thêm số nhà, đường và thành phố.",
        );
      }
    } catch {
      setAddressMessage(
        "Không thể tìm địa chỉ. Kiểm tra cấu hình Stadia hoặc thử lại sau.",
      );
    } finally {
      setSearchingAddress(false);
    }
  }

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
          disabled={disabled || capturingLocation}
          onClick={async () => {
            setCapturingLocation(true);
            setLocationMessage("Đang lấy vị trí thiết bị…");
            try {
              const location = await captureForegroundLocation();
              onCoordinatesChange(
                location.latitude.toFixed(6),
                location.longitude.toFixed(6),
              );
              setMapDestination(null);
              setSelectedAddress(null);
              setLocationMessage(
                `Thiết bị báo sai số khoảng ${Math.round(location.accuracyMeters)} m. Chỉ dùng làm tâm vùng khi bạn đang ở điểm làm việc và đã kiểm tra sai số phù hợp.`,
              );
            } catch (error) {
              setLocationMessage(
                error instanceof LocationCaptureError
                  ? `${error.message} Bạn cũng có thể tìm địa chỉ điểm làm việc hoặc nhập tọa độ đã xác minh.`
                  : "Không thể lấy vị trí thiết bị. Hãy thử lại hoặc nhập tọa độ đã xác minh.",
              );
            } finally {
              setCapturingLocation(false);
            }
          }}
          type="button"
        >
          {capturingLocation
            ? "Đang lấy vị trí…"
            : "Lấy vị trí thiết bị tại văn phòng"}
        </button>
      </div>
      {locationMessage ? (
        <p aria-live="polite" className="mt-2 text-sm text-neutral-700">
          {locationMessage}
        </p>
      ) : null}

      <div className="mt-4 grid min-w-0 gap-2">
        <label className="text-sm font-semibold text-[var(--theme-text)]">
          Đến thành phố
          <input
            className="mt-1 min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)]"
            onChange={(event) => { setCityName(event.target.value); setCityResults([]); }}
            onKeyDown={(event) => {
              if (event.key === "Enter") { event.preventDefault(); void searchCity(); }
            }}
            placeholder="Gõ tên thành phố, ví dụ: Đà Nẵng"
            value={cityName}
          />
        </label>
        <button className="min-h-11 justify-self-start rounded-xl border border-[var(--theme-border)] px-4 text-sm font-semibold text-[var(--theme-text)] hover:bg-[var(--theme-elevated)]" disabled={searchingCity} onClick={() => void searchCity()} type="button">
          {searchingCity ? "Đang tìm…" : "Tìm thành phố"}
        </button>
        {cityMessage ? <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">{cityMessage}</p> : null}
        {cityResults.length > 0 ? (
          <ul aria-label="Kết quả thành phố" className="grid gap-2 sm:grid-cols-2">
            {cityResults.map((city) => (
              <li key={`${city.name}-${city.center.join("-")}`}>
                <button className="min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-left text-sm font-semibold text-[var(--theme-text)] hover:border-primary-600" onClick={() => goToCity(city)} type="button">{city.name}</button>
              </li>
            ))}
          </ul>
        ) : null}
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

      <div className="mt-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 text-[var(--theme-text)] sm:p-4">
        <label
          className="block text-sm font-semibold text-[var(--theme-text)]"
          htmlFor="worksite-address-search"
        >
          Tìm địa chỉ điểm làm việc
        </label>
        <p className="mt-1 text-xs leading-5 text-[var(--theme-muted)]">
          Nhập số nhà, đường, thành phố và quốc gia. Kết quả tìm kiếm chỉ giúp
          di chuyển bản đồ; hãy kiểm tra và xác nhận tâm vùng trước khi lưu.
        </p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            autoComplete="street-address"
            className="min-h-11 min-w-0 flex-1 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)] focus:border-primary-600 focus:outline-2 focus:outline-offset-2 focus:outline-primary-600"
            id="worksite-address-search"
            onChange={(event) => setAddressQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                if (!searchingAddress) void searchAddress();
              }
            }}
            placeholder="Ví dụ: 156A Nguyễn Hữu Thọ, TP. Hồ Chí Minh, Việt Nam"
            value={addressQuery}
          />
          <button
            className="min-h-11 rounded-xl bg-primary-700 px-4 text-sm font-semibold text-white transition-colors hover:bg-primary-800 disabled:opacity-50"
            disabled={searchingAddress}
            onClick={() => void searchAddress()}
            type="button"
          >
            {searchingAddress ? "Đang tìm…" : "Tìm địa chỉ"}
          </button>
        </div>
        {addressMessage ? (
          <p
            aria-live="polite"
            className="mt-2 text-sm text-[var(--theme-muted)]"
          >
            {addressMessage}
          </p>
        ) : null}
        {addressResults.length > 0 ? (
          <ul aria-label="Kết quả tìm địa chỉ" className="mt-3 space-y-2">
            {addressResults.map((result, index) => (
              <li key={`${result.latitude}-${result.longitude}-${index}`}>
                <button
                  aria-pressed={selectedAddress === result.label}
                  className="min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 py-2 text-left text-sm text-[var(--theme-text)] transition-colors hover:border-primary-600 hover:bg-[var(--theme-elevated)] aria-pressed:border-primary-600 aria-pressed:bg-[var(--theme-elevated)]"
                  onClick={() => {
                    setMapDestination([result.latitude, result.longitude]);
                    setDestinationZoom(17);
                    setSelectedAddress(result.label);
                    setAddressMessage(
                      "Đã di chuyển bản đồ. Kiểm tra vị trí trước khi chọn làm tâm vùng.",
                    );
                  }}
                  type="button"
                >
                  {result.label}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {selectedAddress && mapDestination ? (
          <button
            className="mt-3 min-h-11 rounded-xl border border-primary-600 px-4 text-sm font-semibold text-[var(--theme-text)] hover:bg-[var(--theme-elevated)]"
            disabled={disabled}
            onClick={() => {
              onCoordinatesChange(
                mapDestination[0].toFixed(6),
                mapDestination[1].toFixed(6),
              );
              setMapDestination(null);
              setSelectedAddress(null);
              setAddressMessage(
                "Đã chọn tâm vùng. Kiểm tra lại vị trí và bán kính trước khi lưu chính sách.",
              );
            }}
            type="button"
          >
            Chọn vị trí này làm tâm vùng
          </button>
        ) : null}
      </div>

      <div
        aria-label="Bản đồ cấu hình vùng chấm công"
        className="mt-3 overflow-hidden rounded-2xl border border-neutral-200 bg-neutral-100 shadow-inner"
        role="application"
      >
        {satelliteTileConfig ? (
          <div className="flex gap-2 border-b border-[var(--theme-border)] bg-[var(--theme-surface)] p-2" role="group" aria-label="Kiểu bản đồ">
            <button aria-pressed={mapStyle === "street"} className="min-h-10 rounded-lg px-4 text-sm font-semibold text-[var(--theme-text)] aria-pressed:bg-[var(--theme-elevated)]" onClick={() => { setMapStyle("street"); setTilesFailed(false); }} type="button">Đường phố</button>
            <button aria-pressed={mapStyle === "satellite"} className="min-h-10 rounded-lg px-4 text-sm font-semibold text-[var(--theme-text)] aria-pressed:bg-[var(--theme-elevated)]" onClick={() => { setMapStyle("satellite"); setTilesFailed(false); }} type="button">Ảnh vệ tinh</button>
          </div>
        ) : null}
        <MapContainer
          center={mapCenter}
          className="h-72 w-full sm:h-96"
          minZoom={2}
          scrollWheelZoom
          zoom={mapDestination ? destinationZoom : center ? 16 : 2}
        >
          {activeTiles ? (
            <TileLayer
              attribution={activeTiles.attribution}
              eventHandlers={{ tileerror: () => setTilesFailed(true) }}
              key={`${mapStyle}-${tileAttempt}`}
              url={activeTiles.url}
            />
          ) : null}
          <MapViewport
            center={mapDestination ?? center ?? DEFAULT_CENTER}
            zoom={mapDestination ? destinationZoom : center ? 16 : 2}
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
      {tilesFailed || !activeTiles ? (
        <div
          className="mt-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          role="status"
        >
          <p>
            {activeTiles
              ? "Bản đồ nền tạm thời không tải được. Nhập tọa độ trực tiếp ở bên dưới hoặc lấy vị trí thiết bị khi đang ở văn phòng; vùng chấm công vẫn được lưu chính xác."
              : "Chưa cấu hình nguồn bản đồ nền. Hãy nhờ quản trị hệ thống cấu hình bản đồ; trong lúc này có thể nhập tọa độ đã xác minh ở bên dưới."}
          </p>
          {activeTiles ? (
            <button
              className="mt-2 min-h-10 font-bold underline underline-offset-4"
              onClick={() => {
                setTilesFailed(false);
                setTileAttempt((attempt) => attempt + 1);
              }}
              type="button"
            >
              Thử tải lại bản đồ
            </button>
          ) : null}
        </div>
      ) : null}
      <p className="mt-3 text-xs leading-5 text-neutral-500">
        Bản đồ nền có ghi nguồn dữ liệu ngay trên bản đồ. Chỉ Super Admin được cấu hình điểm
        làm việc; vị trí chấm công của nhân viên không được hiển thị tại đây.
      </p>
    </section>
  );
}
