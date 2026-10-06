"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function NavigationLoading() {
  const pathname = usePathname();
  const [visible, setVisible] = useState(false);
  const startTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stopTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const clear = () => {
      if (startTimer.current) clearTimeout(startTimer.current);
      if (stopTimer.current) clearTimeout(stopTimer.current);
      startTimer.current = null;
      stopTimer.current = null;
      setVisible(false);
    };
    const onClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      )
        return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      const link = target.closest<HTMLAnchorElement>("a[href]");
      if (
        !link ||
        link.hasAttribute("download") ||
        (link.target && link.target !== "_self")
      )
        return;
      const destination = new URL(link.href, window.location.href);
      if (
        destination.origin !== window.location.origin ||
        destination.href === window.location.href
      )
        return;
      if (destination.pathname.startsWith("/api/")) return;
      if (
        destination.pathname === window.location.pathname &&
        destination.search === window.location.search
      )
        return;
      clear();
      startTimer.current = setTimeout(() => setVisible(true), 120);
      stopTimer.current = setTimeout(clear, 15_000);
    };
    document.addEventListener("click", onClick, true);
    return () => {
      document.removeEventListener("click", onClick, true);
      clear();
    };
  }, [pathname]);

  return visible ? (
    <div className="navigation-loading" role="status" aria-live="polite">
      <span className="navigation-loading__message">Đang mở trang…</span>
      <span className="navigation-loading__bar" aria-hidden="true" />
    </div>
  ) : null;
}
