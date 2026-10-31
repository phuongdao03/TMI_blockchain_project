"use client";

import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";

const url = "/assets/institution/decision.pdf";

export function DecisionDocumentViewer() {
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState<PDFPageProxy | null>(null);
  const [number, setNumber] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [width, setWidth] = useState(0);
  const [error, setError] = useState(false);
  const [rendered, setRendered] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let disposed = false;
    let task: ReturnType<typeof import("pdfjs-dist").getDocument> | undefined;
    const timeout = window.setTimeout(() => {
      if (!disposed) setError(true);
    }, 20_000);
    async function load() {
      try {
        const pdf = await import("pdfjs-dist");
        if (disposed) return;
        pdf.GlobalWorkerOptions.workerSrc = new URL(
          "pdfjs-dist/build/pdf.worker.min.mjs",
          import.meta.url,
        ).toString();
        task = pdf.getDocument({ url });
        const result = await task.promise;
        if (!disposed) {
          window.clearTimeout(timeout);
          setError(false);
          setDocument(result);
        }
      } catch {
        if (!disposed) setError(true);
      }
    }
    void load();
    return () => {
      disposed = true;
      window.clearTimeout(timeout);
      if (task) void task.destroy();
    };
  }, []);

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(() =>
      setWidth(Math.max(160, element.clientWidth - 24)),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!document) return;
    let disposed = false;
    void document
      .getPage(number)
      .then((result) => {
        if (!disposed) setPage(result);
      })
      .catch(() => {
        if (!disposed) setError(true);
      });
    return () => {
      disposed = true;
    };
  }, [document, number]);

  useEffect(() => {
    if (!page || !width || !canvas.current) return;
    const element = canvas.current;
    const displayWidth = (width * zoom) / 100;
    const scale = displayWidth / page.getViewport({ scale: 1 }).width;
    const ratio = Math.min(
      window.devicePixelRatio || 1,
      2,
      4096 / displayWidth,
    );
    const size = page.getViewport({ scale: scale * ratio });
    element.width = Math.round(size.width);
    element.height = Math.round(size.height);
    element.style.width = `${displayWidth}px`;
    element.style.height = `${size.height / ratio}px`;
    const task = page.render({ canvas: element, viewport: size });
    let disposed = false;
    void task.promise
      .then(() => {
        if (!disposed) setRendered(true);
      })
      .catch((reason: unknown) => {
        if (
          !disposed &&
          (!(reason instanceof Error) ||
            reason.name !== "RenderingCancelledException")
        )
          setError(true);
      });
    return () => {
      disposed = true;
      task.cancel();
    };
  }, [page, width, zoom]);

  function changePage(value: number) {
    setRendered(false);
    setPage(null);
    setNumber(value);
    viewport.current?.scrollTo(0, 0);
  }
  return (
    <div className="decision-reader">
      <nav
        aria-label="Điều khiển văn bản thành lập"
        className="public-media-controls"
      >
        <button
          type="button"
          disabled={!document || number === 1}
          onClick={() => changePage(number - 1)}
        >
          Trang trước
        </button>
        <span role="status">
          Trang {number}/{document?.numPages ?? 2}
        </span>
        <button
          type="button"
          disabled={!document || number === document.numPages}
          onClick={() => changePage(number + 1)}
        >
          Trang sau
        </button>
        <button
          type="button"
          aria-label="Thu nhỏ văn bản"
          disabled={zoom === 100}
          onClick={() => setZoom((value) => value - 25)}
        >
          −
        </button>
        <button
          type="button"
          aria-label="Vừa khung văn bản"
          onClick={() => setZoom(100)}
        >
          {zoom}%
        </button>
        <button
          type="button"
          aria-label="Phóng to văn bản"
          disabled={zoom === 250}
          onClick={() => setZoom((value) => value + 25)}
        >
          +
        </button>
        <a href={url} download>
          Tải PDF gốc
        </a>
        <a href={url} target="_blank" rel="noopener">
          Mở bằng trình duyệt
        </a>
      </nav>
      <div
        ref={viewport}
        className="decision-reader__viewport"
        tabIndex={0}
        aria-label="Nội dung văn bản, có thể cuộn khi phóng to"
      >
        {error ? (
          <p role="alert">
            Chưa xem được văn bản trên thiết bị này. Bạn có thể mở PDF gốc bằng
            trình duyệt ở phía trên.
          </p>
        ) : (
          <>
            {!rendered && <p role="status">Đang tải trang văn bản…</p>}
            <canvas
              ref={canvas}
              role="img"
              aria-label={`Trang ${number} của Quyết định số 55`}
              style={{ visibility: rendered ? "visible" : "hidden" }}
            />
          </>
        )}
      </div>
    </div>
  );
}
