"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function startNavigationFeedback() {
  window.dispatchEvent(new Event("thv:navigation-start"));
}

export function NavigationLoading() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const locationKey = `${pathname}?${searchParams.toString()}`;
  const [visible, setVisible] = useState(false);
  const [slow, setSlow] = useState(false);
  const slowTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const clear = () => {
      delete document.documentElement.dataset.navigationPending;
      if (slowTimer.current) clearTimeout(slowTimer.current);
      slowTimer.current = null;
      setVisible(false);
      setSlow(false);
    };
    const schedule = () => {
      clear();
      document.documentElement.dataset.navigationPending = "true";
      setVisible(true);
      slowTimer.current = setTimeout(() => setSlow(true), 8_000);
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
      schedule();
    };
    const onSubmit = (event: SubmitEvent) => {
      if (event.defaultPrevented || !(event.target instanceof HTMLFormElement))
        return;
      const form = event.target;
      if (
        form.method.toLowerCase() !== "get" ||
        (form.target && form.target !== "_self")
      )
        return;
      const destination = new URL(form.action || window.location.href);
      if (destination.origin === window.location.origin) schedule();
    };
    document.addEventListener("click", onClick, true);
    document.addEventListener("submit", onSubmit);
    window.addEventListener("thv:navigation-start", schedule);
    return () => {
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("submit", onSubmit);
      window.removeEventListener("thv:navigation-start", schedule);
      clear();
    };
  }, [locationKey]);

  return visible ? (
    <div className="navigation-loading" role="status" aria-live="polite">
      <span className="navigation-loading__message">
        <span className="navigation-loading__spinner" aria-hidden="true" />
        {slow ? "Trang phản hồi chậm, vẫn đang tải…" : "Đang mở trang…"}
      </span>
    </div>
  ) : null;
}
