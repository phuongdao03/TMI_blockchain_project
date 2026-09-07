"use client";

import { useCallback, useEffect, useRef } from "react";

import type { ReviewDraft } from "@/lib/api/types";

type AutosaveOptions = {
  draft: ReviewDraft | null;
  onSave: (draft: ReviewDraft) => Promise<void>;
  readOnly: boolean;
  delay?: number;
};

export function useReviewAutosave({
  draft,
  onSave,
  readOnly,
  delay = 650,
}: AutosaveOptions) {
  const lastSaved = useRef(draft ? JSON.stringify(draft) : null);
  const onSaveRef = useRef(onSave);
  const draftRef = useRef(draft);
  const saving = useRef(false);
  const queuedDraft = useRef<ReviewDraft | null>(null);
  const serialized = draft ? JSON.stringify(draft) : null;

  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  const persist = useCallback(async (nextDraft: ReviewDraft) => {
    const nextSerialized = JSON.stringify(nextDraft);
    if (nextSerialized === lastSaved.current) return;
    if (saving.current) {
      queuedDraft.current = nextDraft;
      return;
    }

    saving.current = true;
    let pending: ReviewDraft | null = nextDraft;
    try {
      while (pending) {
        queuedDraft.current = null;
        const pendingSerialized = JSON.stringify(pending);
        if (pendingSerialized !== lastSaved.current) {
          await onSaveRef.current(pending);
          lastSaved.current = pendingSerialized;
        }
        pending = queuedDraft.current;
      }
    } catch {
      queuedDraft.current = null;
    } finally {
      saving.current = false;
    }
  }, []);

  useEffect(() => {
    if (readOnly || !serialized || serialized === lastSaved.current) return;
    const timer = window.setTimeout(() => {
      if (draftRef.current) void persist(draftRef.current);
    }, delay);
    return () => window.clearTimeout(timer);
  }, [delay, persist, readOnly, serialized]);
}
