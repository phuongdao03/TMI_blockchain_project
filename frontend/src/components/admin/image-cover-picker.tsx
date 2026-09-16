"use client";

import Image from "next/image";
import { Check } from "lucide-react";
import { useEffect, useState } from "react";
import { FileUploader } from "@/components/media/file-uploader";
import { WorkCoverPlaceholder } from "@/components/public/work-cover-placeholder";
import { Button } from "@/components/ui/button";
import { publicWorkAdminApi } from "@/lib/api/client";
import type { PublicWorkMedia, PublicWorkPreviewMedia } from "@/lib/api/types";

export function ImageCoverPicker({
  workId,
  title,
  category,
  images,
  items,
  initialSelection,
  onThumbnail,
  onChanged,
}: {
  workId: string;
  title: string;
  category: string;
  images: PublicWorkPreviewMedia[];
  items: PublicWorkMedia[];
  initialSelection?: string;
  onThumbnail: (id: string) => void;
  onChanged: () => void;
}) {
  const [source, setSource] = useState<"submitted" | "upload">("submitted");
  const current = items.find((item) => item.id === initialSelection);
  const [selected, setSelected] = useState<string | null>(current?.id ?? null);
  const [crop, setCrop] = useState({
    x: current?.coverX ?? 50,
    y: current?.coverY ?? 50,
    zoom: current?.coverZoom ?? 100,
  });
  const [previewCrop, setPreviewCrop] = useState(crop);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [failedPreview, setFailedPreview] = useState<string | null>(null);
  const row = items.find((item) => item.id === selected);
  const previewUrl = row
    ? `/api/v1/public/works/${workId}/media/${row.id}?cover=true&coverX=${previewCrop.x}&coverY=${previewCrop.y}&coverZoom=${previewCrop.zoom}`
    : null;
  useEffect(() => {
    const timer = setTimeout(() => setPreviewCrop(crop), 300);
    return () => clearTimeout(timer);
  }, [crop]);
  const choose = (id: string) => {
    const item = items.find((value) => value.id === id);
    setSelected(id);
    setCrop({
      x: item?.coverX ?? 50,
      y: item?.coverY ?? 50,
      zoom: item?.coverZoom ?? 100,
    });
    setSaved(false);
    setError(null);
  };
  const confirm = async () => {
    if (!row) return;
    setSaving(true);
    setError(null);
    try {
      await publicWorkAdminApi.configureCover(workId, row.id, crop);
      onThumbnail(row.mediaAssetId);
      onChanged();
      setSaved(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Chưa lưu được vùng cắt. Vui lòng thử lại.",
      );
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Button
          type="button"
          variant={source === "submitted" ? "default" : "outline"}
          aria-pressed={source === "submitted"}
          onClick={() => setSource("submitted")}
        >
          Chọn ảnh đã nộp
        </Button>
        <Button
          type="button"
          variant={source === "upload" ? "default" : "outline"}
          aria-pressed={source === "upload"}
          onClick={() => setSource("upload")}
        >
          Tải ảnh bìa riêng
        </Button>
      </div>
      <p className="text-xs leading-5 text-neutral-600">
        Ảnh bìa chỉ dùng để trình bày tác phẩm. Không thay đổi tài liệu gốc hoặc
        chứng thư; không sử dụng giấy tờ riêng tư làm bìa.
      </p>
      {source === "upload" ? (
        <FileUploader
          label="Ảnh bìa riêng"
          purpose="PUBLIC_COVER"
          maxFiles={1}
          onComplete={async (asset) => {
            const relation = await publicWorkAdminApi.attachMedia(
              workId,
              asset.id,
              items.length,
              { caption: "Ảnh bìa tác phẩm", altText: `Ảnh bìa: ${title}` },
            );
            onChanged();
            setSelected(relation.id);
            setCrop({ x: 50, y: 50, zoom: 100 });
            setSaved(false);
          }}
        />
      ) : images.length > 0 ? (
        <div
          className="grid grid-cols-2 gap-3"
          aria-label="Ảnh được phép chọn làm bìa"
        >
          {images.map((image) => (
            <button
              key={image.id}
              type="button"
              disabled={saving}
              aria-pressed={image.id === selected}
              aria-label={`Chọn bìa ${image.altText || image.caption || title}`}
              onClick={() => choose(image.id)}
              className={`relative overflow-hidden rounded-xl border-2 text-left ${image.id === selected ? "border-primary-700" : "border-neutral-200"}`}
            >
              <div className="relative aspect-video bg-neutral-100">
                {image.url ? (
                  <Image
                    src={image.url}
                    alt={image.altText || title}
                    fill
                    unoptimized
                    className="object-cover"
                    sizes="(max-width: 640px) 45vw, 300px"
                  />
                ) : null}
              </div>
              <span className="block px-2 py-2 text-xs font-bold break-words">
                {image.caption || image.altText || "Ảnh tác phẩm"}
              </span>
              {image.id === selected ? (
                <span className="absolute top-2 right-2 rounded-full bg-primary-700 p-1 text-white">
                  <Check aria-hidden="true" className="size-4" />
                  <span className="sr-only">Đã chọn</span>
                </span>
              ) : null}
            </button>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-neutral-600">
          Chưa có ảnh tác phẩm phù hợp. Bạn có thể tải ảnh bìa riêng; giấy tờ
          riêng tư không xuất hiện trong danh sách này.
        </p>
      )}
      {row ? (
        <div className="space-y-4">
          <div className="relative aspect-video overflow-hidden rounded-xl bg-neutral-100">
            <Image
              src={previewUrl!}
              alt={`Xem trước vùng cắt: ${title}`}
              fill
              unoptimized
              className="object-cover"
              sizes="(max-width: 640px) 100vw, 800px"
              onError={() => setFailedPreview(previewUrl)}
            />
          </div>
          {failedPreview === previewUrl ? (
            <p role="alert" className="text-sm text-red-800">
              Chưa tải được bản xem trước. Hãy chọn ảnh khác hoặc tải ảnh bìa
              riêng.
            </p>
          ) : null}
          <fieldset disabled={saving} className="space-y-3">
            <legend className="mb-3 text-sm font-bold">
              Điều chỉnh vùng cắt 16:9
            </legend>
            {(
              [
                { key: "x", label: "Vị trí ngang", min: 0, max: 100 },
                { key: "y", label: "Vị trí dọc", min: 0, max: 100 },
                { key: "zoom", label: "Thu phóng", min: 100, max: 300 },
              ] as const
            ).map(({ key, label, min, max }) => (
              <label key={key} className="block text-sm">
                {label} · {crop[key]}%
                <input
                  aria-label={label}
                  type="range"
                  min={min}
                  max={max}
                  value={crop[key]}
                  onChange={(event) => {
                    setCrop((current) => ({
                      ...current,
                      [key]: Number(event.target.value),
                    }));
                    setSaved(false);
                  }}
                  className="block min-h-11 w-full accent-primary-700"
                />
              </label>
            ))}
          </fieldset>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={() => {
                setCrop({ x: 50, y: 50, zoom: 100 });
                setSaved(false);
              }}
            >
              Đặt lại vùng cắt
            </Button>
            <Button
              type="button"
              disabled={saving}
              onClick={() => void confirm()}
            >
              {saving ? "Đang lưu vùng cắt…" : "Dùng ảnh này"}
            </Button>
          </div>
          {saved ? (
            <p role="status" className="text-sm font-semibold text-emerald-800">
              Đã chọn vùng cắt. Bấm Lưu thay đổi để lưu ảnh bìa cho tác phẩm.
            </p>
          ) : (
            <p className="text-xs text-neutral-600">
              Vùng cắt chưa được xác nhận. Bấm Dùng ảnh này khi đã ưng ý.
            </p>
          )}
        </div>
      ) : (
        <WorkCoverPlaceholder title={title} label={category} />
      )}
      {error ? (
        <p role="alert" className="text-sm text-red-800">
          {error}
        </p>
      ) : null}
    </div>
  );
}
