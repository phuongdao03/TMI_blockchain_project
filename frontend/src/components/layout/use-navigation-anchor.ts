"use client";

import { useEffect, useState } from "react";

/** Streaming pages can mount the anchor after Next's first scroll attempt. */
export function useNavigationAnchor(pathname: string, query: string) {
  const [hash, setHash] = useState("");
  useEffect(() => {
    let stopWaiting = () => {};
    const followHash = () => {
      stopWaiting();
      const hash = window.location.hash;
      setHash(hash);
      if (!hash) return;
      let id: string;
      try {
        id = decodeURIComponent(hash.slice(1));
      } catch {
        return;
      }
      let frame = 0;
      const observer = new MutationObserver(() => findTarget());
      const timer = window.setTimeout(() => observer.disconnect(), 10_000);
      const findTarget = () => {
        const target = document.getElementById(id);
        if (!target) return;
        observer.disconnect();
        clearTimeout(timer);
        frame = requestAnimationFrame(() =>
          target.scrollIntoView({ block: "start", behavior: "instant" }),
        );
      };
      observer.observe(document.body, { childList: true, subtree: true });
      findTarget();
      stopWaiting = () => {
        observer.disconnect();
        clearTimeout(timer);
        cancelAnimationFrame(frame);
      };
    };
    followHash();
    window.addEventListener("hashchange", followHash);
    window.addEventListener("popstate", followHash);
    return () => {
      stopWaiting();
      window.removeEventListener("hashchange", followHash);
      window.removeEventListener("popstate", followHash);
    };
  }, [pathname, query]);
  return hash;
}
