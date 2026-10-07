"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function NavigationLoading() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const locationKey = `${pathname}?${searchParams.toString()}`;
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
    const schedule = () => {
      clear();
      startTimer.current = setTimeout(() => setVisible(true), 120);
      stopTimer.current = setTimeout(clear, 15_000);
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
    return () => {
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("submit", onSubmit);
      clear();
    };
  }, [locationKey]);

  return visible ? (
    <div className="navigation-loading" role="status" aria-live="polite">
      <span className="navigation-loading__message">Đang mở trang…</span>
      <span className="navigation-loading__bar" aria-hidden="true" />
    </div>
  ) : null;
}
