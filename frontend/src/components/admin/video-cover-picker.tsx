"use client";

import Image from "next/image";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { publicWorkAdminApi } from "@/lib/api/client";
import type {
  PublicWorkMedia,
  PublicVideoPresentationInput,
} from "@/lib/api/types";

export function VideoCoverPicker({
  item,
  workId,
  posterUrl,
  onChanged,
}: {
  item: PublicWorkMedia;
  workId: string;
  posterUrl: string | null;
  onChanged: () => void;
}) {
  const [time, setTime] = useState(
    item.posterTimeMs == null ? "" : String(item.posterTimeMs / 1000),
  );
  const [selectedTime, setSelectedTime] = useState<number | null>(
    item.posterTimeMs ?? null,
  );
  const [changed, setChanged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null);
  const duration = item.durationMs;
  const candidates = duration
    ? [
        ...new Set(
          [0.1, 0.25, 0.5, 0.75, 0.9].map(
            (ratio) => Math.floor((duration * ratio) / 100) * 100,
          ),
        ),
      ]
    : [0, 3000, 8000, 15000, 30000];
  const frameUrl = (ms: number) =>
    `/api/v1/public/works/${encodeURIComponent(workId)}/media/${encodeURIComponent(item.id)}?poster=true&posterTimeMs=${ms}`;
  const url =
    changed && selectedTime !== null ? frameUrl(selectedTime) : posterUrl;

  const choose = (ms: number) => {
    if (
      !Number.isFinite(ms) ||
      ms < 0 ||
      ms > 86_400_000 ||
      (duration != null && ms >= duration)
    ) {
      setError("Thời điểm lấy bìa phải nằm trong thời lượng video.");
      return;
    }
    setSelectedTime(ms);
    setTime(String(ms / 1000));
    setChanged(true);
    setSaved(false);
    setError(null);
  };
  const save = async () => {
    if (selectedTime === null) return;
    setSaving(true);
    setError(null);
    const settings: PublicVideoPresentationInput = {
      posterMediaAssetId: null,
      posterTimeMs: selectedTime,
      controlsPreset: item.videoControlsPreset,
      fitMode: item.videoFitMode,
      qualityProfile: item.videoQualityProfile,
      maxWidth: item.videoMaxWidth as PublicVideoPresentationInput["maxWidth"],
      autoplay: item.videoAutoplay,
      loop: item.videoLoop,
      muted: item.videoMuted,
    };
    try {
      await publicWorkAdminApi.configureVideo(workId, item.id, settings);
      setSaved(true);
      onChanged();
    } catch {
      setError(
        "Chưa lưu được khung bìa. Hãy thử lại; lựa chọn của bạn vẫn được giữ ở đây.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-4 space-y-4">
      <div className="relative aspect-video w-full max-w-2xl overflow-hidden rounded-xl border bg-neutral-100">
        {url && failedUrl !== url ? (
          <Image
            alt="Ảnh bìa đã chọn"
            fill
            sizes="(max-width: 640px) 100vw, 672px"
            className="object-contain"
            src={url}
            unoptimized
            onError={() => setFailedUrl(url)}
            onLoad={() => setLoadedUrl(url)}
          />
        ) : (
          <p
            className="grid h-full place-content-center p-4 text-center text-sm text-neutral-700"
            role="status"
          >
            Chưa tải được khung này. Chọn thời điểm khác hoặc dùng ảnh đã nộp.
          </p>
        )}
        {url && failedUrl !== url && loadedUrl !== url ? (
          <p
            role="status"
            className="absolute inset-0 grid place-content-center bg-neutral-100/90 p-4 text-center text-sm font-semibold text-neutral-700"
          >
            Đang tải khung hình bìa…
          </p>
        ) : null}
      </div>
      <p className="text-sm leading-6 text-neutral-600">
        Chọn một khung hình nổi bật, tránh đoạn mở đầu tối. Bạn có thể chọn gợi
        ý hoặc nhập chính xác thời điểm bên dưới.
      </p>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        {candidates.map((ms) => (
          <button
            key={ms}
            aria-label={`Chọn khung tại ${ms / 1000} giây`}
            aria-pressed={selectedTime === ms}
            className={`overflow-hidden rounded-lg border bg-white text-sm font-semibold focus-visible:ring-2 focus-visible:ring-primary-500 ${selectedTime === ms ? "border-primary-700 ring-2 ring-primary-700" : "border-neutral-200"}`}
            type="button"
            onClick={() => choose(ms)}
          >
            <span className="relative block aspect-video">
              <Image
                alt=""
                fill
                loading="lazy"
                sizes="128px"
                src={frameUrl(ms)}
                unoptimized
                className="object-cover"
              />
            </span>
            <span className="flex min-h-11 items-center justify-center">
              {ms / 1000}s
            </span>
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="min-w-0 flex-1 text-sm font-bold">
          Thời điểm lấy bìa (giây)
          <input
            className="mt-2 min-h-11 w-full rounded-lg border bg-white px-3"
            type="number"
            min="0"
            max={duration ? (duration - 1) / 1000 : 86400}
            step="0.1"
            inputMode="decimal"
            value={time}
            onChange={(event) => setTime(event.target.value)}
          />
        </label>
        <Button
          type="button"
          variant="outline"
          disabled={time === "" || saving}
          onClick={() => choose(Math.round(Number(time) * 1000))}
        >
          Xem khung hình
        </Button>
        <Button
          type="button"
          className="w-full sm:w-auto"
          disabled={
            saving ||
            selectedTime === null ||
            !url ||
            loadedUrl !== url ||
            (url !== null && failedUrl === url)
          }
          onClick={() => void save()}
        >
          {saving ? "Đang lưu khung bìa…" : "Lưu khung hình làm bìa"}
        </Button>
      </div>
      {error ? (
        <p role="alert" className="text-sm font-semibold text-red-800">
          {error}
        </p>
      ) : null}
      {saved ? (
        <p role="status" className="text-sm font-semibold text-green-800">
          Đã lưu khung bìa. Bấm Lưu thay đổi nếu bạn vừa đổi tài liệu dùng làm
          bìa.
        </p>
      ) : null}
    </div>
  );
}
