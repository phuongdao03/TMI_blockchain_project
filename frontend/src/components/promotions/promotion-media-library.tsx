"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { promotionApi } from "@/lib/api/client";
import type { PromotionMedia } from "@/lib/api/promotion-types";
import { readableError, TextField } from "./form-fields";
import styles from "./promotions.module.css";

export function PromotionMediaLibrary({
  selectMode = false,
  onSelect,
  canManage = true,
}: {
  selectMode?: boolean;
  onSelect?: (asset: PromotionMedia) => void;
  canManage?: boolean;
}) {
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const media = useQuery({
    queryKey: ["promotion-media", page],
    queryFn: () => promotionApi.media(page),
  });
  const [alt, setAlt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [remove, setRemove] = useState<PromotionMedia | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const upload = useMutation({
    mutationFn: () => promotionApi.upload(file!, alt),
    onSuccess: async (asset) => {
      setPage(1);
      await client.invalidateQueries({ queryKey: ["promotion-media"] });
      setFile(null);
      setAlt("");
      if (fileInput.current) fileInput.current.value = "";
      onSelect?.(asset);
    },
  });
  const deletion = useMutation({
    mutationFn: () => promotionApi.deleteMedia(remove!.id),
    onSuccess: async () => {
      setRemove(null);
      await client.invalidateQueries({ queryKey: ["promotion-media"] });
    },
  });
  function choose(selected?: File) {
    setError("");
    if (!selected) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(selected.type)) {
      setError("Chỉ chấp nhận JPG, PNG hoặc WebP.");
      return;
    }
    if (selected.size > 5 * 1024 * 1024) {
      setError("Ảnh phải có dung lượng tối đa 5 MB.");
      return;
    }
    setFile(selected);
  }
  return (
    <div className={styles.stack}>
      {canManage && (
        <form
          className={styles.stack}
          onSubmit={(e) => {
            e.preventDefault();
            upload.mutate();
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            choose(e.dataTransfer.files[0]);
          }}
        >
          <label className={styles.field}>
            <span>Kéo ảnh vào đây hoặc chọn từ máy tính</span>
            <input
              ref={fileInput}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => choose(e.target.files?.[0])}
            />
          </label>
          <p className={styles.muted}>
            {file
              ? `${file.name} · ${Math.ceil(file.size / 1024)} KB`
              : "JPG, PNG, WebP · Tối đa 5 MB. Ảnh sẽ được kiểm tra và loại bỏ metadata trên máy chủ."}
          </p>
          <TextField
            label="Mô tả ảnh (Alt text)"
            required
            maxLength={255}
            value={alt}
            onChange={(e) => setAlt(e.target.value)}
          />
          <Button
            type="submit"
            disabled={!file || !alt.trim() || upload.isPending}
          >
            {upload.isPending ? "Đang tải ảnh…" : "Tải ảnh lên"}
          </Button>
          {(error || upload.isError) && (
            <p role="alert" className={styles.error}>
              {error || readableError(upload.error)}
            </p>
          )}
        </form>
      )}
      {media.isPending && <p role="status">Đang tải thư viện ảnh…</p>}
      {media.isError && (
        <p role="alert" className={styles.error}>
          {readableError(media.error)}
        </p>
      )}
      {media.data?.items.length === 0 && (
        <p className={styles.empty}>Chưa có ảnh trong thư viện.</p>
      )}
      <div className={styles.mediaGrid}>
        {media.data?.items.map((asset) => (
          <article key={asset.id} className={styles.panel}>
            <Image
              className={styles.mediaImage}
              src={asset.url}
              alt={asset.altText}
              width={asset.width}
              height={asset.height}
              unoptimized
            />
            <p className="mt-2 break-words text-sm">{asset.altText}</p>
            <p className={styles.muted}>
              {asset.width} × {asset.height} · {Math.ceil(asset.size / 1024)} KB
            </p>
            <div className={`${styles.actions} mt-3`}>
              {selectMode && (
                <Button variant="outline" onClick={() => onSelect?.(asset)}>
                  Chọn ảnh
                </Button>
              )}
              {canManage && !selectMode && (
                <Button variant="ghost" onClick={() => setRemove(asset)}>
                  Xóa ảnh
                </Button>
              )}
            </div>
          </article>
        ))}
      </div>
      <div className={styles.actions}>
        <Button
          variant="outline"
          disabled={page === 1 || media.isFetching}
          onClick={() => setPage(page - 1)}
        >
          Trang trước
        </Button>
        <span>
          Trang {page} · {media.data?.total ?? 0} ảnh
        </span>
        <Button
          variant="outline"
          disabled={
            !media.data ||
            page * media.data.pageSize >= media.data.total ||
            media.isFetching
          }
          onClick={() => setPage(page + 1)}
        >
          Trang sau
        </Button>
      </div>
      <ConfirmationDialog
        open={Boolean(remove)}
        title="Xóa ảnh khỏi thư viện?"
        description="Ảnh đã được sử dụng trong lịch sử ưu đãi vẫn được bảo toàn theo chính sách lưu trữ."
        confirmLabel="Xóa ảnh"
        isPending={deletion.isPending}
        onCancel={() => setRemove(null)}
        onConfirm={() => deletion.mutate()}
      >
        {deletion.isError && (
          <p role="alert" className={styles.error}>
            {readableError(deletion.error)}
          </p>
        )}
      </ConfirmationDialog>
    </div>
  );
}
