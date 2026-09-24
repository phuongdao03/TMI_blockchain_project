"use client";

import "leaflet/dist/leaflet.css";

import { Fragment, useEffect } from "react";
import {
  Circle,
  CircleMarker,
  MapContainer,
  TileLayer,
  useMap,
} from "react-leaflet";

import type { AttendanceLocationEvidenceReview } from "@/lib/api/types";

type EvidencePoint = {
  id: string;
  eventType: AttendanceLocationEvidenceReview["eventType"];
  latitude: number;
  longitude: number;
  accuracyMeters: number;
};

const OSM_TILE_URL =
  process.env.NEXT_PUBLIC_OSM_TILE_URL ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

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
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url={OSM_TILE_URL}
          />
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
      <p className="px-3 py-2 text-xs leading-5 text-neutral-600">
        Chấm xanh: giờ vào · Chấm đỏ: giờ ra · Vòng tròn: sai số GPS do thiết bị
        báo.
      </p>
    </div>
  );
}
