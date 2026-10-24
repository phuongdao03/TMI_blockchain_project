"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CircleAlert, LoaderCircle, Megaphone } from "lucide-react";
import { useState, type FormEvent } from "react";

import { advertisingApi } from "@/lib/api/client";
import type { AdvertisingCampaignSummary } from "@/lib/api/types";
import { Button } from "@/components/ui/button";

const inputClassName =
  "min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)] outline-none focus-visible:ring-2 focus-visible:ring-primary-500";

export function AdvertisingCreativeEditPanel({
  campaign,
  onClose,
  onDone,
}: {
  campaign: AdvertisingCampaignSummary;
  onClose: () => void;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(campaign.creativeTitle ?? "");
  const [description, setDescription] = useState(campaign.creativeDescription ?? "");
  const [imageUrl, setImageUrl] = useState(campaign.imageUrl ?? "");
  const [destinationUrl, setDestinationUrl] = useState(campaign.destinationUrl ?? "");
  const [feedback, setFeedback] = useState("");
  const [savedForRetry, setSavedForRetry] = useState(false);

  const submit = useMutation({
    mutationFn: () => advertisingApi.submitCampaign(campaign.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["advertising-campaigns"] });
      onDone();
    },
    onError: () => setFeedback("Nội dung đã lưu nhưng chưa gửi lại được. Hãy thử gửi duyệt lại."),
  });
  const save = useMutation({
    mutationFn: async () => {
      await advertisingApi.updateCreative(campaign.id, {
        title: title.trim(),
        description: description.trim(),
        imageUrl: imageUrl.trim() || null,
        destinationUrl: destinationUrl.trim(),
      });
      try {
        await advertisingApi.submitCampaign(campaign.id);
        return true;
      } catch {
        return false;
      }
    },
    onSuccess: async (submitted) => {
      if (submitted) {
        await queryClient.invalidateQueries({ queryKey: ["advertising-campaigns"] });
        onDone();
        return;
      }
      setSavedForRetry(true);
      setFeedback("Đã lưu nội dung mới. Hệ thống chưa gửi duyệt lại được, bạn có thể thử lại ngay.");
    },
    onError: () => setFeedback("Không lưu được nội dung. Vui lòng kiểm tra đường dẫn và thử lại."),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback("");
    setSavedForRetry(false);
    save.mutate();
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--theme-border)] p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary-800">
            <Megaphone aria-hidden="true" className="size-5" />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--theme-muted)]">Cập nhật theo phản hồi duyệt</p>
            <h2 className="mt-1 text-lg font-bold">{campaign.creativeTitle}</h2>
            <p className="mt-1 text-sm text-[var(--theme-muted)]">{campaign.placementName}</p>
          </div>
        </div>
        <Button onClick={onClose} variant="ghost">Đóng</Button>
      </div>

      {campaign.creativeReviewNote ? (
        <p className="mx-4 mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950 sm:mx-5">
          <strong>Góp ý của quản trị viên:</strong> {campaign.creativeReviewNote}
        </p>
      ) : null}

      <form className="grid gap-4 p-4 sm:p-5 lg:grid-cols-2" onSubmit={handleSubmit}>
        <label className="space-y-1.5 text-sm font-semibold lg:col-span-2">
          <span>Tiêu đề nội dung</span>
          <input className={inputClassName} disabled={savedForRetry} maxLength={200} minLength={2} onChange={(event) => setTitle(event.target.value)} required value={title} />
        </label>
        <label className="space-y-1.5 text-sm font-semibold lg:col-span-2">
          <span>Mô tả nội dung</span>
          <textarea className={`${inputClassName} min-h-28 py-2`} disabled={savedForRetry} maxLength={5000} onChange={(event) => setDescription(event.target.value)} value={description} />
        </label>
        <label className="space-y-1.5 text-sm font-semibold">
          <span>Đường dẫn ảnh (không bắt buộc)</span>
          <input className={inputClassName} disabled={savedForRetry} onChange={(event) => setImageUrl(event.target.value)} type="url" value={imageUrl} />
        </label>
        <label className="space-y-1.5 text-sm font-semibold">
          <span>Liên kết đích</span>
          <input className={inputClassName} disabled={savedForRetry} inputMode="url" onChange={(event) => setDestinationUrl(event.target.value)} placeholder="https://... hoặc /duong-dan" required value={destinationUrl} />
        </label>

        {feedback ? (
          <p className="flex gap-2 rounded-xl bg-[var(--theme-elevated)] p-3 text-sm leading-6 lg:col-span-2" role="status">
            <CircleAlert aria-hidden="true" className="mt-1 size-4 shrink-0" /> {feedback}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2 lg:col-span-2">
          {savedForRetry ? (
            <>
              <Button disabled={submit.isPending} onClick={() => submit.mutate()} type="button">
                {submit.isPending ? <LoaderCircle aria-hidden="true" className="thv-loading-spinner size-4" /> : null}
                Gửi lại để duyệt <ArrowRight aria-hidden="true" className="size-4" />
              </Button>
              <Button disabled={submit.isPending} onClick={() => setSavedForRetry(false)} type="button" variant="outline">Chỉnh sửa thêm</Button>
            </>
          ) : (
            <Button disabled={save.isPending || !title.trim() || !destinationUrl.trim()} type="submit">
              {save.isPending ? <LoaderCircle aria-hidden="true" className="thv-loading-spinner size-4" /> : null}
              Lưu nội dung và gửi duyệt <ArrowRight aria-hidden="true" className="size-4" />
            </Button>
          )}
          <p className="self-center text-xs text-[var(--theme-muted)]">Chiến dịch sẽ chờ quản trị viên duyệt lại trước khi đặt lịch.</p>
        </div>
      </form>
    </section>
  );
}
