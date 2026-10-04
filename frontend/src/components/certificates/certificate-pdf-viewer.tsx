"use client";

import {
  Download,
  Expand,
  ExternalLink,
  FileText,
  Minus,
  Plus,
  Shrink,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { PDFPageProxy } from "pdfjs-dist";

import { certificateApi } from "@/lib/api/client";

type Props = {
  certificateId: string;
  certificateNumber: string;
  onDownload: () => void;
};

export function CertificatePdfViewer({
  certificateId,
  certificateNumber,
  onDownload,
}: Props) {
  const [page, setPage] = useState<PDFPageProxy | null>(null);
  const [error, setError] = useState(false);
  const [pdfAvailable, setPdfAvailable] = useState(false);
  const [nativeFallback, setNativeFallback] = useState(false);
  const [reload, setReload] = useState(0);
  const [width, setWidth] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [expanded, setExpanded] = useState(false);
  const [nativeFullscreen, setNativeFullscreen] = useState(false);
  const readerRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfUrl = `/api/v1/certificates/${encodeURIComponent(certificateId)}/pdf?inline=1`;

  useEffect(() => {
    let disposed = false;
    let loadingTask:
      | ReturnType<typeof import("pdfjs-dist").getDocument>
      | undefined;

    async function load() {
      try {
        setPage(null);
        setError(false);
        setNativeFallback(false);
        setPdfAvailable(false);
        const blob = await certificateApi.downloadPdf(certificateId);
        if (disposed) return;
        setPdfAvailable(true);

        try {
          const pdfjs = await import("pdfjs-dist");
          pdfjs.GlobalWorkerOptions.workerSrc = new URL(
            "pdfjs-dist/build/pdf.worker.min.mjs",
            import.meta.url,
          ).toString();
          loadingTask = pdfjs.getDocument({
            data: new Uint8Array(await blob.arrayBuffer()),
          });
          const pdfDocument = await loadingTask.promise;
          const firstPage = await pdfDocument.getPage(1);
          if (!disposed) setPage(firstPage);
        } catch {
          if (!disposed) setNativeFallback(true);
        }
      } catch {
        if (!disposed) setError(true);
      }
    }

    void load();
    return () => {
      disposed = true;
      if (loadingTask) void loadingTask.destroy();
    };
  }, [certificateId, reload]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const observer = new ResizeObserver(() => {
      setWidth(Math.max(240, viewport.clientWidth - 24));
    });
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!page || !width || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const natural = page.getViewport({ scale: 1 });
    const displayWidth = (width * zoom) / 100;
    const displayScale = displayWidth / natural.width;
    const displayHeight = natural.height * displayScale;
    const resolution = Math.min(
      window.devicePixelRatio || 1,
      2,
      4096 / displayWidth,
    );
    canvas.width = Math.round(displayWidth * resolution);
    canvas.height = Math.round(displayHeight * resolution);
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;
    const renderTask = page.render({
      canvas,
      viewport: page.getViewport({ scale: displayScale * resolution }),
    });
    void renderTask.promise.catch((reason: unknown) => {
      if (
        reason instanceof Error &&
        reason.name === "RenderingCancelledException"
      )
        return;
      setNativeFallback(true);
    });
    return () => renderTask.cancel();
  }, [page, width, zoom]);

  useEffect(() => {
    const syncFullscreen = () =>
      setNativeFullscreen(document.fullscreenElement === readerRef.current);
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () =>
      document.removeEventListener("fullscreenchange", syncFullscreen);
  }, []);

  useEffect(() => {
    if (!expanded) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [expanded]);

  async function toggleFullscreen() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    if (document.fullscreenElement === readerRef.current) {
      await document.exitFullscreen();
      return;
    }
    try {
      if (!readerRef.current?.requestFullscreen)
        throw new Error("Fullscreen unavailable");
      await readerRef.current.requestFullscreen();
    } catch {
      setExpanded(true);
    }
  }

  const buttonClass =
    "inline-flex min-h-10 items-center justify-center gap-1.5 rounded-md px-2.5 text-sm font-medium text-white hover:bg-white/15 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-300 disabled:opacity-40";

  return (
    <section aria-label="Bằng xác lập PDF" className="min-w-0">
      <div
        className={`overflow-hidden rounded-xl border border-neutral-300 bg-[#292929] shadow-lg ${expanded ? "fixed inset-0 z-[100] flex flex-col rounded-none" : ""}`}
        onKeyDown={(event) => {
          if (event.key === "Escape" && expanded) setExpanded(false);
        }}
        ref={readerRef}
      >
        <div className="grid grid-cols-[1fr_auto] items-center gap-y-1 border-b border-white/15 bg-[#343434] p-2 text-white sm:flex sm:gap-2 sm:px-4">
          <div className="flex min-w-0 items-center gap-2 px-2 sm:mr-auto">
            <FileText aria-hidden="true" className="size-4 shrink-0" />
            <span className="truncate text-sm font-semibold">
              Bằng xác lập.pdf
            </span>
          </div>
          <span
            className="px-1 text-xs text-white/70"
            aria-label="Trang 1 trên 1"
          >
            1 / 1
          </span>
          <div className="flex items-center border-l border-white/20 pl-1 sm:pl-2">
            <button
              aria-label="Thu nhỏ PDF"
              className={buttonClass}
              disabled={zoom <= 50}
              onClick={() => setZoom((value) => Math.max(50, value - 25))}
              type="button"
            >
              <Minus className="size-4" />
            </button>
            <button
              aria-label="Vừa khung"
              className={`${buttonClass} min-w-14 tabular-nums`}
              onClick={() => setZoom(100)}
              type="button"
            >
              {zoom}%
            </button>
            <button
              aria-label="Phóng to PDF"
              className={buttonClass}
              disabled={zoom >= 300}
              onClick={() => setZoom((value) => Math.min(300, value + 25))}
              type="button"
            >
              <Plus className="size-4" />
            </button>
          </div>
          <div className="flex items-center border-l border-white/20 pl-1 sm:pl-2">
            <button
              aria-label={
                expanded || nativeFullscreen
                  ? "Thoát toàn màn hình"
                  : "Xem toàn màn hình"
              }
              className={buttonClass}
              onClick={() => void toggleFullscreen()}
              type="button"
            >
              {expanded || nativeFullscreen ? (
                <Shrink className="size-4" />
              ) : (
                <Expand className="size-4" />
              )}
            </button>
            <button
              aria-label="Mở PDF trong thẻ mới"
              className={buttonClass}
              disabled={!pdfAvailable}
              onClick={() =>
                window.open(pdfUrl, "_blank", "noopener,noreferrer")
              }
              type="button"
            >
              <ExternalLink className="size-4" />
            </button>
            <button
              aria-label="Tải PDF"
              className={buttonClass}
              onClick={onDownload}
              type="button"
            >
              <Download className="size-4" />
            </button>
          </div>
        </div>
        <div
          aria-label={`Nội dung bằng xác lập ${certificateNumber}`}
          className={`overflow-auto p-3 ${expanded || nativeFullscreen ? "min-h-0 flex-1" : "max-h-[75dvh] min-h-48"}`}
          ref={viewportRef}
          role="region"
          tabIndex={0}
        >
          {error ? (
            <div
              className="grid min-h-48 place-items-center gap-3 text-center text-sm text-white"
              role="alert"
            >
              <p>Chưa tải được bằng xác lập. Vui lòng thử lại.</p>
              <button
                className={buttonClass}
                onClick={() => setReload((value) => value + 1)}
                type="button"
              >
                Tải lại PDF
              </button>
            </div>
          ) : nativeFallback && pdfAvailable ? (
            <div className="grid min-h-48 place-content-center gap-3 px-4 text-center text-sm text-white">
              <p>Bản PDF này cần trình xem của trình duyệt.</p>
              <a
                className={buttonClass}
                href={pdfUrl}
                rel="noopener noreferrer"
                target="_blank"
              >
                Mở bằng xác lập PDF
                <ExternalLink aria-hidden="true" className="size-4" />
              </a>
            </div>
          ) : !page ? (
            <div
              className="grid min-h-48 place-items-center text-sm text-white/80"
              role="status"
            >
              Đang mở bằng xác lập…
            </div>
          ) : (
            <canvas
              aria-label="Trang 1 của bằng xác lập PDF"
              className="mx-auto bg-white shadow-xl"
              ref={canvasRef}
              role="img"
            />
          )}
        </div>
      </div>
    </section>
  );
}
