"use client";

import { useEffect, useRef, useState } from "react";
import type { ComponentType } from "react";

export function DeferredProposalViewer() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [Viewer, setViewer] = useState<ComponentType | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let mounted = true;
    const load = () => {
      void import("./proposal-viewer")
        .then(({ ProposalViewer }) => {
          if (mounted) setViewer(() => ProposalViewer);
        })
        .catch(() => {
          if (mounted) setFailed(true);
        });
    };

    const host = hostRef.current;
    if (!host || !("IntersectionObserver" in window)) {
      load();
      return () => {
        mounted = false;
      };
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          observer.disconnect();
          load();
        }
      },
      { rootMargin: "600px" },
    );
    observer.observe(host);
    return () => {
      mounted = false;
      observer.disconnect();
    };
  }, []);

  return (
    <div aria-busy={!Viewer && !failed} ref={hostRef}>
      {Viewer ? (
        <Viewer />
      ) : (
        <div className="proposal-reader-deferred__placeholder" role="status">
          <p>
            {failed
              ? "Chưa mở được trình đọc trên thiết bị này."
              : "Đang chuẩn bị trình đọc tài liệu…"}
          </p>
          {failed ? (
            <a
              href="/assets/institution/proposal-2026.pdf"
              target="_blank"
              rel="noopener"
            >
              Mở proposal PDF
            </a>
          ) : null}
        </div>
      )}
    </div>
  );
}
