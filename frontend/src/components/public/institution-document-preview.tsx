"use client";

import Image from "next/image";
import { useEffect, useState, type ComponentType } from "react";
import { PublicMediaDialog } from "./public-media-dialog";

export function InstitutionDocumentPreview() {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const [Viewer, setViewer] = useState<ComponentType | null>(null);
  const [readerFailed, setReaderFailed] = useState(false);
  useEffect(() => {
    if (!open || Viewer) return;
    let mounted = true;
    const timeout = window.setTimeout(() => {
      if (mounted) setReaderFailed(true);
    }, 20_000);
    void import("./decision-document-viewer")
      .then(({ DecisionDocumentViewer }) => {
        if (mounted) {
          setViewer(() => DecisionDocumentViewer);
          setReaderFailed(false);
        }
      })
      .catch(() => {
        if (mounted) setReaderFailed(true);
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      mounted = false;
      window.clearTimeout(timeout);
    };
  }, [open, Viewer]);
  return (
    <div className="institution-document">
      <button
        className="institution-document__preview"
        aria-label="Xem văn bản đầy đủ"
        type="button"
        onClick={() => setOpen(true)}
      >
        {failed ? (
          <span>Ảnh xem trước chưa tải được. Mở văn bản đầy đủ để đọc.</span>
        ) : (
          <Image
            alt="Trang đầu Quyết định số 55 về việc thành lập Trung tâm Xác lập Tinh Hoa Việt"
            src="/assets/institution/decision-preview.jpg"
            width={700}
            height={984}
            sizes="(max-width: 48rem) 82vw, 450px"
            onError={() => setFailed(true)}
          />
        )}
        <span className="institution-document__caption">
          Quyết định thành lập · PDF gốc, 2 trang
        </span>
      </button>
      <div className="institution-actions">
        <button
          type="button"
          className="institution-button institution-button--primary"
          onClick={() => setOpen(true)}
        >
          Xem văn bản đầy đủ
        </button>
        <a
          className="institution-button"
          href="/assets/institution/decision.pdf"
          download
        >
          Tải PDF · 2 trang
        </a>
      </div>
      <a
        className="institution-document__native"
        href="/assets/institution/decision.pdf"
        target="_blank"
        rel="noopener"
      >
        Mở PDF bằng trình duyệt
      </a>
      {open && (
        <PublicMediaDialog
          title="Quyết định số 55 — Văn bản thành lập"
          closeLabel="Đóng văn bản thành lập"
          onClose={() => setOpen(false)}
        >
          {Viewer ? (
            <Viewer />
          ) : (
            <div
              className="public-media-loading"
              role={readerFailed ? "alert" : "status"}
            >
              <p>
                {readerFailed
                  ? "Chưa mở được trình xem trên thiết bị này."
                  : "Đang chuẩn bị văn bản…"}
              </p>
              <a
                href="/assets/institution/decision.pdf"
                target="_blank"
                rel="noopener"
              >
                Mở PDF gốc bằng trình duyệt
              </a>
            </div>
          )}
        </PublicMediaDialog>
      )}
    </div>
  );
}
