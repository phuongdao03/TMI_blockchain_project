"use client";

import { Search, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { createPortal } from "react-dom";
import { SearchAutocomplete } from "@/components/search/search-autocomplete";
import { useNavigationOverlay } from "./use-navigation-overlay";
import { startNavigationFeedback } from "@/components/ui/navigation-loading";

export function NavigationSearch({ identity = "" }: { identity?: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [portalTarget, setPortalTarget] = useState<Element | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const close = (restore = true) => {
    setOpen(false);
    if (restore) requestAnimationFrame(() => trigger.current?.focus());
  };
  useNavigationOverlay(open, panel, close, identity);
  return (
    <>
      <button
        ref={trigger}
        className="navigation-icon-button"
        aria-label="Mở tìm kiếm"
        aria-expanded={open}
        aria-controls="navigation-search"
        onClick={(event) => {
          setPortalTarget(event.currentTarget.closest(".public-shell"));
          setOpen(true);
        }}
        type="button"
      >
        <Search aria-hidden="true" size={21} />
      </button>
      {open &&
        createPortal(
          <div className="navigation-search-overlay">
            <button
              className="navigation-search-backdrop"
              aria-label="Đóng tìm kiếm"
              tabIndex={-1}
              onClick={() => close()}
              type="button"
            />
            <div
              ref={panel}
              id="navigation-search"
              className="navigation-search-panel public-theme-surface"
              role="dialog"
              aria-modal="true"
              aria-labelledby="navigation-search-title"
            >
              <h2 id="navigation-search-title">Tìm kiếm đề cử</h2>
              <form
                action="/works"
                method="get"
                onSubmit={(event) => {
                  event.preventDefault();
                  const query = String(
                    new FormData(event.currentTarget).get("query") ?? "",
                  )
                    .trim()
                    .slice(0, 200);
                  close(false);
                  startNavigationFeedback();
                  router.push(
                    `/works${query ? `?${new URLSearchParams({ query })}` : ""}`,
                  );
                }}
              >
                <SearchAutocomplete autoFocus showClear />
                <button className="navigation-search-submit" type="submit">
                  Tìm kiếm
                </button>
              </form>
              <Link href="/verify" onClick={() => close(false)}>
                Bạn cần tra cứu bằng xác lập?
              </Link>
              <button
                className="navigation-icon-button navigation-search-close"
                aria-label="Đóng tìm kiếm"
                onClick={() => close()}
                type="button"
              >
                <X aria-hidden="true" />
              </button>
            </div>
          </div>,
          portalTarget ?? document.body,
        )}
    </>
  );
}
