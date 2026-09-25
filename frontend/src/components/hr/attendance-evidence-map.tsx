"use client";

import "leaflet/dist/leaflet.css";

import { Fragment, useEffect, useState } from "react";
import {
  Circle,
  CircleMarker,
  MapContainer,
  TileLayer,
  useMap,
} from "react-leaflet";

import type { AttendanceLocationEvidenceReview } from "@/lib/api/types";
import { mapTileConfig } from "@/lib/maps/tile-config";

type EvidencePoint = {
  id: string;
  eventType: AttendanceLocationEvidenceReview["eventType"];
  latitude: number;
  longitude: number;
  accuracyMeters: number;
};

function MapViewport({ points }: { points: EvidencePoint[] }) {
  const map = useMap();

  useEffect(() => {
    const first = points[0];
    if (!first) return;
    if (points.length === 1) {
      map.setView([first.latitude, first.longitude], 16, { animate: false });
    } else if (points.length > 1) {
      map.fitBounds(
        points.map((point) => [point.latitude, point.longitude]),
        {
          animate: false,
          maxZoom: 16,
          padding: [32, 32],
        },
      );
    }
  }, [map, points]);

  return null;
}

export function AttendanceEvidenceMap({
  evidence,
}: {
  evidence: AttendanceLocationEvidenceReview[];
}) {
  const [tilesFailed, setTilesFailed] = useState(false);
  const points = evidence.flatMap((item): EvidencePoint[] => {
    const latitude = Number(item.latitude);
    const longitude = Number(item.longitude);
    if (
      item.latitude === null ||
      item.longitude === null ||
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      Math.abs(latitude) > 90 ||
      Math.abs(longitude) > 180
    ) {
      return [];
    }
    return [
      {
        id: item.id,
        eventType: item.eventType,
        latitude,
        longitude,
        accuracyMeters: Number(item.accuracyMeters),
      },
    ];
  });

  const first = points[0];
  if (!first) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-neutral-200 bg-neutral-100">
      <div aria-label="Bản đồ vị trí chấm công của nhân viên" role="img">
        <MapContainer
          center={[first.latitude, first.longitude]}
          className="h-64 w-full sm:h-80"
          scrollWheelZoom={false}
          zoom={16}
        >
          {!tilesFailed && mapTileConfig ? <TileLayer
            attribution={mapTileConfig.attribution}
            eventHandlers={{ tileerror: () => setTilesFailed(true) }}
            url={mapTileConfig.url}
          /> : null}
          <MapViewport points={points} />
          {points.map((point) => {
            const color =
              point.eventType === "CHECK_IN" ? "#047857" : "#9d0000";
            return (
              <Fragment key={point.id}>
                <CircleMarker
                  center={[point.latitude, point.longitude]}
                  fillColor={color}
                  fillOpacity={1}
                  pathOptions={{ color: "#ffffff", weight: 3 }}
                  radius={8}
                />
                {Number.isFinite(point.accuracyMeters) &&
                point.accuracyMeters > 0 ? (
                  <Circle
                    center={[point.latitude, point.longitude]}
                    fillColor={color}
                    fillOpacity={0.12}
                    pathOptions={{ color, weight: 1.5 }}
                    radius={point.accuracyMeters}
                  />
                ) : null}
              </Fragment>
            );
          })}
        </MapContainer>
      </div>
      {tilesFailed || !mapTileConfig ? <p className="px-3 py-2 text-sm text-amber-900" role="status">Bản đồ nền không khả dụng; dữ liệu vị trí đã ghi nhận vẫn được giữ nguyên.</p> : null}
      <p className="px-3 py-2 text-xs leading-5 text-neutral-600">
        Chấm xanh: giờ vào · Chấm đỏ: giờ ra · Vòng tròn: sai số GPS do thiết bị
        báo.
      </p>
    </div>
  );
}
