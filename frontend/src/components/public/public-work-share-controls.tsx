"use client";

import { Download, Flag, Link2, QrCode, Share2, X } from "lucide-react";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { PublicContentReportDialog } from "@/components/public/public-content-report-dialog";
import { emitPublicWorkAction } from "@/lib/analytics/public-work-actions";
import { publicApi } from "@/lib/api/client";
import type { PublicWorkDetail } from "@/lib/api/types";

export function canonicalBrowserWorkUrl(slug: string, origin: string): string {
  const base = new URL(origin);
  return new URL(`/works/${encodeURIComponent(slug)}`, base.origin).href;
}

export function PublicWorkShareControls({
  detail,
}: {
  detail: PublicWorkDetail;
}) {
  const [status, setStatus] = useState("");
  const [qrOpen, setQrOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const canonicalUrl = () =>
    canonicalBrowserWorkUrl(detail.canonicalSlug, window.location.origin);
  const recordShare = (channel: "NATIVE" | "COPY_LINK") => {
    void publicApi
      .recordShare(detail.canonicalSlug, channel)
      .catch(() => undefined);
  };

  const share = async () => {
    emitPublicWorkAction({
      action: "share",
      workId: detail.id,
      slug: detail.canonicalSlug,
    });
    try {
      if (navigator.share) {
        await navigator.share({
          title: detail.title,
          text: detail.shortDescription,
          url: canonicalUrl(),
        });
        recordShare("NATIVE");
        setStatus("Đã mở tùy chọn chia sẻ.");
      } else {
        await copyCanonicalUrl();
      }
    } catch (error) {
      setStatus(
        error instanceof DOMException && error.name === "AbortError"
          ? "Đã hủy chia sẻ."
          : "Chưa thể chia sẻ từ trình duyệt này.",
      );
    }
  };

  const copyCanonicalUrl = async () => {
    try {
      await navigator.clipboard.writeText(canonicalUrl());
      recordShare("COPY_LINK");
      setStatus("Đã sao chép liên kết chính thức.");
    } catch {
      setStatus("Không thể sao chép. Hãy dùng thanh địa chỉ trình duyệt.");
    }
  };

  const openQr = () => {
    emitPublicWorkAction({
      action: "qr_requested",
      workId: detail.id,
      slug: detail.canonicalSlug,
    });
    setQrOpen(true);
  };

  return (
    <section
      aria-label="Tác vụ công khai"
      className="mt-10 flex flex-wrap items-center gap-3 border-t border-white/10 pt-6"
    >
      <Button onClick={share} variant="outline">
        <Share2 className="size-4" /> Chia sẻ
      </Button>
      <Button onClick={copyCanonicalUrl} variant="ghost">
        <Link2 className="size-4" /> Sao chép liên kết
      </Button>
      <Button onClick={openQr} variant="ghost">
        <QrCode className="size-4" /> QR
      </Button>
      <Button
        onClick={() => {
          emitPublicWorkAction({
            action: "report_requested",
            workId: detail.id,
            slug: detail.slug,
          });
          setReportOpen(true);
        }}
        variant="ghost"
      >
        <Flag className="size-4" /> Báo cáo
      </Button>
      <p aria-live="polite" className="basis-full text-xs text-slate-400">
        {status}
      </p>
      {qrOpen ? (
        <QrDialog detail={detail} onClose={() => setQrOpen(false)} />
      ) : null}
      {reportOpen ? (
        <PublicContentReportDialog
          detail={detail}
          onClose={() => setReportOpen(false)}
        />
      ) : null}
    </section>
  );
}

function QrDialog({
  detail,
  onClose,
}: {
  detail: PublicWorkDetail;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const qrUrl = `/api/v1/public/works/${encodeURIComponent(detail.canonicalSlug)}/qr`;

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button, a[href], [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus();
    };
  }, [onClose]);

  return (
    <div
      aria-labelledby="public-work-qr-title"
      aria-modal="true"
      className="fixed inset-0 z-50 grid place-items-center bg-ink-950/85 p-4 backdrop-blur-sm"
      ref={dialogRef}
      role="dialog"
    >
      <div className="w-full max-w-md rounded-3xl border border-white/15 bg-ink-900 p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-5">
          <div>
            <p className="text-xs font-bold tracking-[0.18em] text-gold-300 uppercase">
              Liên kết công khai
            </p>
            <h2
              className="mt-2 text-2xl font-bold text-white"
              id="public-work-qr-title"
            >
              Quét để mở tác phẩm
            </h2>
          </div>
          <button
            aria-label="Đóng mã QR"
            className="grid size-11 place-items-center rounded-full border border-white/15 text-slate-300 hover:bg-white/10"
            onClick={onClose}
            ref={closeRef}
            type="button"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="mx-auto mt-6 w-fit rounded-2xl bg-white p-4">
          <Image
            alt={`Mã QR mở tác phẩm ${detail.title}`}
            height={256}
            src={qrUrl}
            unoptimized
            width={256}
          />
        </div>
        <p className="mt-5 text-sm leading-6 text-slate-400">
          QR chỉ chứa địa chỉ chính thức của tác phẩm, không chứa token hay dữ
          liệu hồ sơ riêng tư.
        </p>
        <a
          className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-white px-4 text-sm font-bold text-ink-950"
          download={`${detail.canonicalSlug}-qr.png`}
          href={qrUrl}
        >
          <Download className="size-4" /> Tải mã QR
        </a>
      </div>
    </div>
  );
}
