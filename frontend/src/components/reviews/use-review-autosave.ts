"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
  const [savedValue, setSavedValue] = useState(
    draft ? JSON.stringify(draft) : null,
  );
  const [saveState, setSaveState] = useState<"idle" | "saving" | "error">(
    "idle",
  );
  const lastSaved = useRef(draft ? JSON.stringify(draft) : null);
  const onSaveRef = useRef(onSave);
  const draftRef = useRef(draft);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const serialized = draft ? JSON.stringify(draft) : null;

  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  const persist = useCallback((nextDraft: ReviewDraft) => {
    const task = queue.current.then(async () => {
      const nextSerialized = JSON.stringify(nextDraft);
      if (nextSerialized === lastSaved.current) return;
      setSaveState("saving");
      try {
        await onSaveRef.current(nextDraft);
        lastSaved.current = nextSerialized;
        setSavedValue(nextSerialized);
        setSaveState("idle");
      } catch (error) {
        setSaveState("error");
        throw error;
      }
    });
    queue.current = task.catch(() => undefined);
    return task;
  }, []);

  useEffect(() => {
    if (readOnly || !serialized || serialized === lastSaved.current) return;
    const timer = window.setTimeout(() => {
      if (draftRef.current)
        void persist(draftRef.current).catch(() => undefined);
    }, delay);
    return () => window.clearTimeout(timer);
  }, [delay, persist, readOnly, serialized]);

  const status =
    saveState === "error"
      ? "error"
      : saveState === "saving"
        ? "saving"
        : serialized !== savedValue
          ? "pending"
          : "saved";
  useEffect(() => {
    if (readOnly || status === "saved") return;
    const protectDraft = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", protectDraft);
    return () => window.removeEventListener("beforeunload", protectDraft);
  }, [readOnly, status]);
  return { status, save: persist };
}
