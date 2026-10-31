"use client";

import { useEffect, useRef, type RefObject } from "react";
import { usePathname, useSearchParams } from "next/navigation";

/** One lifecycle for navigation panels: route changes never leave a scroll lock. */
export function useNavigationOverlay(
  open: boolean,
  panel: RefObject<HTMLElement | null>,
  close: (restoreFocus?: boolean) => void,
  identity = "",
) {
  const pathname = usePathname();
  const params = useSearchParams();
  const destination = `${pathname}?${params.toString()}|${identity}`;
  const closeRef = useRef(close);
  useEffect(() => {
    closeRef.current = close;
  });
  const previousDestination = useRef(destination);
  useEffect(() => {
    const changed = previousDestination.current !== destination;
    previousDestination.current = destination;
    if (changed && open) closeRef.current(false);
  }, [destination, open]);

  useEffect(() => {
    if (!open) return;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusables = () =>
      Array.from(
        panel.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), summary, [tabindex="0"]',
        ) ?? [],
      ).filter(
        (element) =>
          !element.closest("[hidden]") &&
          getComputedStyle(element).display !== "none" &&
          getComputedStyle(element).visibility !== "hidden",
      );
    // Layout has settled before moving focus into a newly mounted panel.
    const frame = requestAnimationFrame(() => focusables()[0]?.focus());
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const elements = focusables();
      const first = elements[0];
      const last = elements.at(-1);
      if (!first || !last) return;
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          !panel.current?.contains(document.activeElement))
      ) {
        event.preventDefault();
        last.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          !panel.current?.contains(document.activeElement))
      ) {
        event.preventDefault();
        first.focus();
      }
    };
    const navigate = () => closeRef.current(false);
    const desktop = window.matchMedia("(min-width: 64rem)");
    const resize = () => closeRef.current();
    document.addEventListener("keydown", keyboard);
    window.addEventListener("hashchange", navigate);
    window.addEventListener("popstate", navigate);
    desktop.addEventListener("change", resize);
    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = overflow;
      document.removeEventListener("keydown", keyboard);
      window.removeEventListener("hashchange", navigate);
      window.removeEventListener("popstate", navigate);
      desktop.removeEventListener("change", resize);
    };
  }, [open, panel]);
}
