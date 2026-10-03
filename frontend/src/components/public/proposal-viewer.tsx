"use client";

import Image from "next/image";
import {
  BookOpenText,
  ChevronLeft,
  ChevronRight,
  Expand,
  ExternalLink,
  List,
  Minus,
  Plus,
  Shrink,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent, TouchEvent } from "react";

import pageText from "./proposal-page-text.json";

const PDF = "/assets/institution/proposal-2026.pdf";
const TOTAL_PAGES = pageText.length;
const outline = [
  [1, "Trang bìa"],
  [2, "Mục lục"],
  [3, "Lời ngỏ"],
  [4, "Dấu ấn thực tế"],
  [7, "Cơ sở pháp lý"],
  [10, "Mục đích, yêu cầu và ý nghĩa"],
  [12, "Thông tin chương trình"],
  [14, "Đối tượng tham gia"],
  [17, "Nội dung và kịch bản"],
  [21, "Nguồn lực và các gói tài trợ"],
  [23, "Nguyên tắc quyền lợi"],
  [25, "So sánh các gói tài trợ"],
  [26, "Tài trợ Độc quyền"],
  [29, "Tài trợ Kim cương"],
  [32, "Tài trợ Vàng"],
  [34, "Tài trợ Bạc"],
  [36, "Tài trợ Đồng"],
  [38, "Đồng tài trợ"],
  [41, "Triển khai và nghiệm thu"],
  [46, "Tiến độ đồng hành"],
  [47, "Tiến độ tổ chức"],
  [48, "Phân công nhiệm vụ"],
  [49, "Kinh phí và nguyên tắc"],
  [50, "Các cơ quan đưa tin"],
  [51, "Thông tin văn bản"],
  [52, "Lời mời đồng hành"],
  [53, "Lời cảm ơn"],
] as const;

function clampPage(page: number) {
  return Math.min(TOTAL_PAGES, Math.max(1, page));
}

function pageTitle(page: number) {
  return (
    [...outline].reverse().find(([start]) => start <= page)?.[1] ?? "Trang bìa"
  );
}

export function ProposalViewer() {
  const [page, setPage] = useState(1);
  const [pageInput, setPageInput] = useState("1");
  const [zoom, setZoom] = useState(100);
  const [outlineOpen, setOutlineOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fallbackFullscreen, setFallbackFullscreen] = useState(false);
  const readerRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const touchStart = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const syncFullscreen = () =>
      setFullscreen(document.fullscreenElement === readerRef.current);
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () =>
      document.removeEventListener("fullscreenchange", syncFullscreen);
  }, []);

  useEffect(() => {
    if (!fallbackFullscreen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [fallbackFullscreen]);

  function goToPage(next: number) {
    const target = clampPage(next);
    setPage(target);
    setPageInput(String(target));
    if (viewportRef.current) {
      viewportRef.current.scrollTop = 0;
      viewportRef.current.scrollLeft = 0;
    }
  }

  function submitPage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const requested = Number(pageInput);
    if (Number.isInteger(requested)) goToPage(requested);
    else setPageInput(String(page));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape" && fallbackFullscreen) {
      setFallbackFullscreen(false);
      return;
    }
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement
    )
      return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      goToPage(page + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      goToPage(page - 1);
    }
  }

  function handleTouchEnd(event: TouchEvent<HTMLDivElement>) {
    const touch = event.changedTouches[0];
    if (!touchStart.current || !touch || zoom > 100) return;
    const dx = touch.clientX - touchStart.current.x;
    const dy = touch.clientY - touchStart.current.y;
    if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.3) {
      goToPage(page + (dx < 0 ? 1 : -1));
    }
    touchStart.current = null;
  }

  async function toggleFullscreen() {
    if (fallbackFullscreen) {
      setFallbackFullscreen(false);
      return;
    }
    if (document.fullscreenElement === readerRef.current) {
      await document.exitFullscreen();
    } else {
      try {
        if (!readerRef.current?.requestFullscreen)
          throw new Error("Fullscreen unavailable");
        await readerRef.current.requestFullscreen();
      } catch {
        setFallbackFullscreen(true);
      }
    }
  }

  const currentSection = outline.findIndex(
    ([start], index) =>
      start <= page && (outline[index + 1]?.[0] ?? TOTAL_PAGES + 1) > page,
  );

  return (
    <div className="proposal-reader-wrap">
      <div
        aria-label="Trình xem proposal"
        className={`proposal-reader${fallbackFullscreen ? " proposal-reader--expanded" : ""}`}
        onKeyDown={handleKeyDown}
        ref={readerRef}
        role="region"
        tabIndex={0}
      >
        <div className="proposal-reader__topbar">
          <div className="proposal-reader__brand">
            <BookOpenText aria-hidden="true" size={24} strokeWidth={1.8} />
            <span>
              <strong>TINH HOA VIỆT</strong>
              <small>Hồ sơ chương trình · 2026</small>
            </span>
          </div>
          <div className="proposal-reader__toolbar">
            <button
              aria-controls="proposal-outline"
              aria-expanded={outlineOpen}
              className="proposal-reader__button"
              onClick={() => setOutlineOpen(!outlineOpen)}
              type="button"
            >
              <List aria-hidden="true" size={18} /> Mục lục
            </button>
            <button
              className="proposal-reader__button proposal-reader__button--primary"
              onClick={toggleFullscreen}
              type="button"
            >
              {fullscreen || fallbackFullscreen ? (
                <Shrink aria-hidden="true" size={18} />
              ) : (
                <Expand aria-hidden="true" size={18} />
              )}
              {fullscreen || fallbackFullscreen
                ? "Thoát toàn màn hình"
                : "Đọc toàn màn hình"}
            </button>
          </div>
        </div>

        <div className="proposal-reader__layout">
          {outlineOpen && (
            <nav
              aria-label="Mục lục proposal"
              className="proposal-reader__outline"
              id="proposal-outline"
            >
              <div className="proposal-reader__outline-head">
                <strong>Mục lục</strong>
                <button
                  aria-label="Đóng mục lục"
                  className="proposal-reader__icon-button"
                  onClick={() => setOutlineOpen(false)}
                  type="button"
                >
                  <X aria-hidden="true" size={18} />
                </button>
              </div>
              <div className="proposal-reader__outline-list">
                {outline.map(([start, label], index) => (
                  <button
                    aria-current={
                      currentSection === index ? "location" : undefined
                    }
                    aria-label={`${label}, trang ${start}`}
                    className="proposal-reader__outline-item"
                    key={start}
                    onClick={() => {
                      goToPage(start);
                      setOutlineOpen(false);
                    }}
                    type="button"
                  >
                    <span>{label}</span>
                    <span>{String(start).padStart(2, "0")}</span>
                  </button>
                ))}
              </div>
            </nav>
          )}

          <div className="proposal-reader__main">
            <div
              aria-label="Nội dung trang proposal; dùng phím mũi tên trái và phải để chuyển trang"
              className="proposal-reader__viewport"
              onTouchEnd={handleTouchEnd}
              onTouchStart={(event) => {
                const touch = event.touches[0];
                if (touch)
                  touchStart.current = { x: touch.clientX, y: touch.clientY };
              }}
              ref={viewportRef}
              tabIndex={0}
            >
              <div
                className="proposal-reader__page"
                style={{ width: `${zoom}%` }}
              >
                <Image
                  alt={`Proposal Tinh Hoa Việt — trang ${page} trên ${TOTAL_PAGES}: ${pageTitle(page)}`}
                  height={900}
                  loading="lazy"
                  priority={false}
                  src={`/assets/institution/proposal-pages/page-${String(page).padStart(2, "0")}.webp`}
                  unoptimized
                  width={1600}
                />
              </div>
            </div>
            <p className="proposal-reader__status" role="status">
              Trang {page} / {TOTAL_PAGES} · {pageTitle(page)}
            </p>
            <div className="proposal-reader__controls">
              <button
                aria-label="Trang trước"
                className="proposal-reader__button proposal-reader__button--nav"
                disabled={page === 1}
                onClick={() => goToPage(page - 1)}
                type="button"
              >
                <ChevronLeft aria-hidden="true" size={20} />
                <span>Trang trước</span>
              </button>
              <form
                className="proposal-reader__page-form"
                onSubmit={submitPage}
              >
                <label className="sr-only" htmlFor="proposal-page-input">
                  Số trang muốn xem
                </label>
                <input
                  id="proposal-page-input"
                  inputMode="numeric"
                  max={TOTAL_PAGES}
                  min={1}
                  onChange={(event) => setPageInput(event.target.value)}
                  type="number"
                  value={pageInput}
                />
                <span>/ {TOTAL_PAGES}</span>
                <button className="sr-only" type="submit">
                  Đi đến trang
                </button>
              </form>
              <button
                aria-label="Trang sau"
                className="proposal-reader__button proposal-reader__button--nav proposal-reader__button--primary"
                disabled={page === TOTAL_PAGES}
                onClick={() => goToPage(page + 1)}
                type="button"
              >
                <span>Trang sau</span>
                <ChevronRight aria-hidden="true" size={20} />
              </button>
              <div
                aria-label="Phóng to nội dung"
                className="proposal-reader__zoom"
                role="group"
              >
                <button
                  aria-label="Thu nhỏ trang"
                  disabled={zoom === 100}
                  onClick={() => setZoom(Math.max(100, zoom - 25))}
                  type="button"
                >
                  <Minus aria-hidden="true" size={19} />
                </button>
                <button
                  aria-label="Đặt lại mức phóng to"
                  onClick={() => setZoom(100)}
                  type="button"
                >
                  {zoom}%
                </button>
                <button
                  aria-label="Phóng to trang"
                  disabled={zoom === 200}
                  onClick={() => setZoom(Math.min(200, zoom + 25))}
                  type="button"
                >
                  <Plus aria-hidden="true" size={19} />
                </button>
              </div>
            </div>
            <div className="proposal-reader__track">
              <span>01</span>
              <label className="sr-only" htmlFor="proposal-page-slider">
                Chọn trang proposal
              </label>
              <input
                aria-valuetext={`Trang ${page} trên ${TOTAL_PAGES}: ${pageTitle(page)}`}
                id="proposal-page-slider"
                max={TOTAL_PAGES}
                min={1}
                onChange={(event) => goToPage(Number(event.target.value))}
                style={{
                  backgroundSize: `${((page - 1) / (TOTAL_PAGES - 1)) * 100}% 100%`,
                }}
                type="range"
                value={page}
              />
              <span>{TOTAL_PAGES}</span>
            </div>
            <details className="proposal-reader__text">
              <summary>Đọc nội dung chữ của trang này</summary>
              <pre>{pageText[page - 1]}</pre>
            </details>
          </div>
        </div>
      </div>
      <div className="proposal-reader__footer">
        <p>Vuốt để lật trang · Dùng phím mũi tên để chuyển trang.</p>
        <a href={`${PDF}#page=${page}`} rel="noopener" target="_blank">
          Mở bản PDF gốc <ExternalLink aria-hidden="true" size={16} />
        </a>
      </div>
      <noscript>
        <a href={PDF}>Mở proposal PDF 53 trang</a>
      </noscript>
    </div>
  );
}
