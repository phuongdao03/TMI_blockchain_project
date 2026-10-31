"use client";
import { useEffect, useRef, useState, type ComponentType } from "react";
export function DeferredProposalViewer() {
  const container = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);
  const [Viewer, setViewer] = useState<ComponentType | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!container.current) return;
    if (!window.IntersectionObserver) {
      queueMicrotask(() => setNear(true));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!near || Viewer) return;
    let active = true;
    const timeout = window.setTimeout(() => {
      if (active) setFailed(true);
    }, 20_000);
    void import("./proposal-viewer")
      .then(({ ProposalViewer }) => {
        if (active) {
          setViewer(() => ProposalViewer);
          setFailed(false);
        }
      })
      .catch(() => {
        if (active) setFailed(true);
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      active = false;
      clearTimeout(timeout);
    };
  }, [near, Viewer, attempt]);
  return (
    <div
      ref={container}
      className="proposal-inline"
      aria-label="Đọc tài liệu giới thiệu ngay trên trang"
    >
      {Viewer ? (
        <Viewer />
      ) : (
        <div
          className="public-media-loading"
          role={failed ? "alert" : "status"}
        >
          <p>
            {failed
              ? "Chưa tải được trình đọc. Vui lòng thử lại."
              : "Đang chuẩn bị tài liệu để đọc ngay tại đây…"}
          </p>
          {failed && (
            <button
              type="button"
              className="institution-button"
              onClick={() => {
                setFailed(false);
                setAttempt((value) => value + 1);
              }}
            >
              Thử lại trình đọc
            </button>
          )}
        </div>
      )}
    </div>
  );
}
