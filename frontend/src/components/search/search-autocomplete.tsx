"use client";

import { FolderTree, Search, Tag } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { publicApi } from "@/lib/api/client";
import type {
  SearchAutocompleteKind,
  SearchAutocompleteSuggestion,
} from "@/lib/api/types";

const DEBOUNCE_MS = 250;

export function SearchAutocomplete({
  defaultValue = "",
  name = "query",
}: {
  defaultValue?: string;
  name?: string;
}) {
  const router = useRouter();
  const listId = useId();
  const [query, setQuery] = useState(defaultValue);
  const [suggestions, setSuggestions] = useState<
    SearchAutocompleteSuggestion[]
  >([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const normalized = query.trim();
    if (normalized.length < 2) {
      return;
    }
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setLoading(true);
      setFailed(false);
      try {
        const result = await publicApi.autocomplete(
          normalized,
          controller.signal,
        );
        setSuggestions(result);
        setActiveIndex(-1);
        setOpen(true);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setSuggestions([]);
        setFailed(true);
        setOpen(true);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query]);

  function selectSuggestion(item: SearchAutocompleteSuggestion) {
    setOpen(false);
    router.push(suggestionHref(item));
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (
      !suggestions.length ||
      !["ArrowDown", "ArrowUp", "Enter"].includes(event.key)
    )
      return;
    if (event.key === "Enter" && activeIndex >= 0) {
      const selected = suggestions[activeIndex];
      if (selected) {
        event.preventDefault();
        selectSuggestion(selected);
      }
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      const direction = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) => {
        const next = current + direction;
        if (next < 0) return suggestions.length - 1;
        return next % suggestions.length;
      });
    }
  }

  return (
    <div className="relative min-w-0 flex-1">
      <label htmlFor={`${listId}-input`} className="sr-only">
        Tìm đề cử
      </label>
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute top-4 left-4 z-10 size-4 text-slate-500"
      />
      <input
        aria-activedescendant={
          activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined
        }
        aria-autocomplete="list"
        aria-controls={listId}
        aria-expanded={open}
        autoComplete="off"
        className="min-h-12 w-full rounded-xl border border-white/10 bg-ink-950 pr-12 pl-11 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-gold-300 focus:ring-2 focus:ring-gold-300/20"
        id={`${listId}-input`}
        maxLength={200}
        name={name}
        onChange={(event) => {
          const value = event.target.value;
          setQuery(value);
          if (value.trim().length < 2) {
            setSuggestions([]);
            setOpen(false);
            setLoading(false);
            setFailed(false);
          }
        }}
        onFocus={() => suggestions.length && setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="Tìm đề cử, danh mục hoặc chủ đề"
        role="combobox"
        type="search"
        value={query}
      />
      <span aria-live="polite" className="sr-only">
        {loading
          ? "Đang tìm gợi ý"
          : open
            ? `${suggestions.length} gợi ý tìm kiếm`
            : ""}
      </span>
      {open ? (
        <div className="absolute inset-x-0 top-[calc(100%+0.5rem)] z-30 overflow-hidden rounded-xl border border-white/10 bg-ink-900 shadow-2xl shadow-black/40">
          {loading ? (
            <AutocompleteLoading />
          ) : failed ? (
            <p className="px-4 py-4 text-sm text-slate-400" role="status">
              Chưa thể tải gợi ý. Bạn vẫn có thể nhấn Enter để tìm kiếm.
            </p>
          ) : suggestions.length ? (
            <ul aria-label="Gợi ý tìm kiếm" id={listId} role="listbox">
              {suggestions.map((item, index) => (
                <li
                  aria-selected={activeIndex === index}
                  className="group flex cursor-pointer items-center gap-3 border-b border-white/[0.06] px-4 py-3 text-sm text-slate-200 transition last:border-b-0 hover:bg-white/[0.06] aria-selected:bg-gold-300/10 aria-selected:text-white"
                  id={`${listId}-${index}`}
                  key={`${item.kind}-${item.slug}`}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    selectSuggestion(item);
                  }}
                  role="option"
                >
                  <SuggestionIcon kind={item.kind} />
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {item.label}
                  </span>
                  <span className="text-[0.68rem] font-semibold tracking-[0.12em] text-slate-500 uppercase group-aria-selected:text-gold-300">
                    {kindLabel(item.kind)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-4 text-sm text-slate-400" role="status">
              Không có gợi ý công khai phù hợp.
            </p>
          )}
          <p className="border-t border-white/[0.06] px-4 py-2 text-[0.7rem] text-slate-600">
            ↑↓ để di chuyển · Enter để chọn · Esc để đóng
          </p>
        </div>
      ) : null}
    </div>
  );
}

function AutocompleteLoading() {
  return (
    <div aria-label="Đang tải gợi ý" className="space-y-px p-2">
      {[0, 1, 2].map((item) => (
        <div
          className="h-11 animate-pulse rounded-lg bg-white/[0.05]"
          key={item}
        />
      ))}
    </div>
  );
}

function SuggestionIcon({ kind }: { kind: SearchAutocompleteKind }) {
  const Icon = kind === "category" ? FolderTree : kind === "tag" ? Tag : Search;
  return (
    <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-white/[0.05] text-gold-300">
      <Icon aria-hidden="true" className="size-4" />
    </span>
  );
}

function kindLabel(kind: SearchAutocompleteKind) {
  return kind === "work"
    ? "Tác phẩm"
    : kind === "category"
      ? "Danh mục"
      : "Chủ đề";
}

function suggestionHref(item: SearchAutocompleteSuggestion) {
  const slug = encodeURIComponent(item.slug);
  if (item.kind === "work") return `/works/${slug}`;
  return `/search?${item.kind === "category" ? "category" : "tags"}=${slug}`;
}
