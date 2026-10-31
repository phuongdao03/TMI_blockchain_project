"use client";

import Image from "next/image";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { PublicMediaDialog } from "./public-media-dialog";

export function HeritageLightbox({
  photo,
  index,
  total,
  onMove,
  onClose,
}: {
  photo: { file: string; title: string; category: string };
  index: number;
  total: number;
  onMove: (direction: number) => void;
  onClose: () => void;
}) {
  const [zoom, setZoom] = useState(100);
  const [failed, setFailed] = useState<string>();
  const [loaded, setLoaded] = useState<string>();
  useEffect(() => {
    if (loaded === photo.file || failed === photo.file) return;
    const timeout = window.setTimeout(() => setFailed(photo.file), 15_000);
    return () => window.clearTimeout(timeout);
  }, [photo.file, loaded, failed]);
  const touch = useRef<{ x: number; y: number } | null>(null);
  function move(direction: number) {
    setZoom(100);
    onMove(direction);
  }
  useEffect(() => {
    function keyboard(event: KeyboardEvent) {
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        event.preventDefault();
        setZoom(100);
        onMove(event.key === "ArrowLeft" ? -1 : 1);
      }
    }
    document.addEventListener("keydown", keyboard);
    return () => document.removeEventListener("keydown", keyboard);
  }, [onMove]);
  return (
    <PublicMediaDialog
      title="Ảnh Tinh Hoa Việt"
      closeLabel="Đóng ảnh toàn màn hình"
      onClose={onClose}
    >
      <nav className="public-media-controls" aria-label="Điều khiển bộ ảnh">
        <button
          aria-label="Ảnh trước trong bộ sưu tập"
          type="button"
          onClick={() => move(-1)}
        >
          <ArrowLeft aria-hidden="true" size={20} />
        </button>
        <span role="status">
          Ảnh {index + 1}/{total}
        </span>
        <button
          aria-label="Ảnh tiếp theo trong bộ sưu tập"
          type="button"
          onClick={() => move(1)}
        >
          <ArrowRight aria-hidden="true" size={20} />
        </button>
        <button
          aria-label="Phóng to ảnh"
          aria-pressed={zoom > 100}
          type="button"
          onClick={() => setZoom((value) => (value === 100 ? 200 : 100))}
        >
          {zoom === 100 ? "Phóng to" : "Vừa khung"}
        </button>
      </nav>
      <div
        className="heritage-lightbox__viewport"
        tabIndex={0}
        aria-label="Ảnh lớn, có thể cuộn khi phóng to"
        onTouchStart={(event) => {
          const point = event.touches[0];
          touch.current =
            event.touches.length === 1 && point
              ? { x: point.clientX, y: point.clientY }
              : null;
        }}
        onTouchEnd={(event) => {
          const point = event.changedTouches[0];
          if (touch.current && point && zoom === 100) {
            const dx = point.clientX - touch.current.x;
            const dy = point.clientY - touch.current.y;
            if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.3)
              move(dx < 0 ? 1 : -1);
          }
          touch.current = null;
        }}
      >
        {failed === photo.file ? (
          <p role="alert">
            Ảnh chưa tải được. Bạn có thể chuyển sang ảnh tiếp theo.
          </p>
        ) : (
          <div
            className="heritage-lightbox__image"
            style={{ width: `${zoom}%` }}
          >
            <Image
              alt={photo.title}
              width={1600}
              height={1100}
              sizes={zoom > 100 ? "200vw" : "100vw"}
              src={`/assets/institution/${photo.file}`}
              onError={() => setFailed(photo.file)}
              onLoad={() => setLoaded(photo.file)}
            />
          </div>
        )}
      </div>
      {loaded !== photo.file && failed !== photo.file && (
        <p role="status" className="heritage-lightbox__caption">
          Đang tải ảnh lớn…
        </p>
      )}
      <p className="heritage-lightbox__caption">
        {photo.category} · {photo.title}
      </p>
    </PublicMediaDialog>
  );
}
