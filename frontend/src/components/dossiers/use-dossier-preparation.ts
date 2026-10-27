"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, dossierApi } from "@/lib/api/client";
import type {
  DossierPreparationPayload,
  DossierPreparationState,
} from "@/lib/api/types";
import { subscribeToAuthSessionChanges } from "@/lib/auth/session-sync";
import {
  clearPreparationBackup,
  EMPTY_PREPARATION,
  readPreparationBackup,
  serializePreparation,
  writePreparationBackup,
} from "./preparation-recovery-storage";

function verifyOwner(state: DossierPreparationState, userId: string) {
  if (state.ownerUserId !== userId)
    throw new ApiError(
      "Phiên đăng nhập đã thay đổi.",
      "PREPARATION_OWNER_CHANGED",
      403,
    );
}

export function useDossierPreparation({
  userId,
  value,
  onRestore,
  delay = 650,
}: {
  userId?: string;
  value: DossierPreparationPayload;
  onRestore: (payload: DossierPreparationPayload) => void;
  delay?: number;
}) {
  const [ready, setReady] = useState(!userId);
  const [loadedUserId, setLoadedUserId] = useState<string>();
  const [revisionValue, setRevisionValue] = useState(0);
  const [saved, setSaved] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState<DossierPreparationState | null>(
    null,
  );
  const [storageError, setStorageError] = useState(false);
  const [recovered, setRecovered] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const revision = useRef(0);
  const latest = useRef(value);
  const restore = useRef(onRestore);
  const acknowledged = useRef<string | null>(null);
  const scope = useRef<{
    active: boolean;
    completed: boolean;
    owner: string;
  } | null>(null);
  const inFlight = useRef<Promise<void> | null>(null);
  const memoryBackup = useRef<{
    owner: string;
    revision: number;
    payload: DossierPreparationPayload;
  } | null>(null);
  const serialized = serializePreparation(value);
  useEffect(() => {
    latest.current = value;
    restore.current = onRestore;
  }, [value, onRestore]);

  useEffect(() => {
    if (!userId) return;
    const current = { active: true, completed: false, owner: userId };
    scope.current = current;
    inFlight.current = null;
    queueMicrotask(() => {
      if (current.active) {
        setReady(false);
        setSaving(false);
        setError("");
        setConflict(null);
        setRecovered(false);
      }
    });
    void dossierApi
      .getPreparation()
      .then((remote) => {
        if (!current.active) return;
        verifyOwner(remote, userId);
        const backup =
          readPreparationBackup(userId) ??
          (memoryBackup.current?.owner === userId
            ? memoryBackup.current
            : null);
        memoryBackup.current = null;
        const remoteValue = remote.payload ?? EMPTY_PREPARATION;
        revision.current = remote.revision;
        setRevisionValue(remote.revision);
        acknowledged.current = serializePreparation(remoteValue);
        setSaved(acknowledged.current);
        if (
          backup &&
          serializePreparation(backup.payload) !== acknowledged.current
        ) {
          restore.current(backup.payload);
          setRecovered(true);
          if (backup.revision !== remote.revision) {
            revision.current = backup.revision;
            setConflict(remote);
          }
        } else {
          restore.current(remoteValue);
          setRecovered(Boolean(remote.payload));
          clearPreparationBackup(userId);
        }
        setReady(true);
        setLoadedUserId(userId);
      })
      .catch((failure) => {
        if (!current.active) return;
        if (
          failure instanceof ApiError &&
          failure.code === "PREPARATION_OWNER_CHANGED"
        ) {
          setError(
            "Phiên đăng nhập đã thay đổi. Hãy khôi phục lại sau khi tài khoản được cập nhật.",
          );
          return;
        }
        const backup = readPreparationBackup(userId);
        if (backup) {
          revision.current = backup.revision;
          setRevisionValue(backup.revision);
          acknowledged.current = null;
          setSaved(null);
          restore.current(backup.payload);
          setRecovered(true);
          setReady(true);
          setLoadedUserId(userId);
        }
        setError(
          "Chưa tải được dữ liệu trên tài khoản. Bản khôi phục tạm vẫn được giữ; vui lòng thử lại.",
        );
      });
    const unsubscribe = subscribeToAuthSessionChanges(() => {
      if (serializePreparation(latest.current) !== acknowledged.current)
        memoryBackup.current = {
          owner: userId,
          revision: revision.current,
          payload: latest.current,
        };
      current.active = false;
      clearPreparationBackup(userId);
      setReady(false);
      setError(
        "Phiên đăng nhập đã thay đổi. Hãy khôi phục lại để tiếp tục an toàn.",
      );
    });
    return () => {
      current.active = false;
      unsubscribe();
    };
  }, [userId, attempt]);

  const persist = useCallback((): Promise<void> => {
    const current = scope.current;
    if (!current?.active || current.completed || !userId)
      return Promise.resolve();
    if (serializePreparation(latest.current) === acknowledged.current)
      return Promise.resolve();
    if (inFlight.current) return inFlight.current;
    const task = async () => {
      if (!current.active || current.completed) return;
      setSaving(true);
      setError("");
      try {
        while (current.active && !current.completed) {
          const pending = latest.current;
          const pendingSerialized = serializePreparation(pending);
          if (pendingSerialized === acknowledged.current) break;
          setStorageError(
            !writePreparationBackup(userId, revision.current, pending),
          );
          const result = await dossierApi.savePreparation(
            userId,
            revision.current,
            pending,
          );
          if (!current.active || current.completed) return;
          verifyOwner(result, userId);
          revision.current = result.revision;
          setRevisionValue(result.revision);
          acknowledged.current = pendingSerialized;
          setSaved(pendingSerialized);
          if (serializePreparation(latest.current) === pendingSerialized)
            clearPreparationBackup(userId);
          else
            setStorageError(
              !writePreparationBackup(userId, revision.current, latest.current),
            );
        }
      } catch (failure) {
        if (!current.active || current.completed) return;
        if (failure instanceof ApiError && failure.status === 409) {
          try {
            const remote = await dossierApi.getPreparation();
            if (current.active && !current.completed) {
              verifyOwner(remote, userId);
              if (
                serializePreparation(remote.payload ?? EMPTY_PREPARATION) ===
                serializePreparation(latest.current)
              ) {
                revision.current = remote.revision;
                setRevisionValue(remote.revision);
                acknowledged.current = serializePreparation(latest.current);
                setSaved(acknowledged.current);
                clearPreparationBackup(userId);
              } else setConflict(remote);
            }
          } catch {
            if (current.active)
              setError(
                "Chưa kiểm tra được bản trên tài khoản. Nội dung đang nhập vẫn được giữ.",
              );
          }
        } else
          setError(
            "Chưa đồng bộ được. Nội dung đang nhập vẫn được giữ; vui lòng thử lưu lại.",
          );
      } finally {
        if (current.active && !current.completed) setSaving(false);
        if (scope.current === current) inFlight.current = null;
      }
    };
    inFlight.current = Promise.resolve().then(task);
    return inFlight.current;
  }, [userId]);

  useEffect(() => {
    if (
      !userId ||
      !ready ||
      loadedUserId !== userId ||
      scope.current?.completed ||
      serialized === acknowledged.current
    )
      return;
    setStorageError(
      !writePreparationBackup(userId, revision.current, latest.current),
    );
    if (conflict) return;
    const timer = window.setTimeout(() => void persist(), delay);
    return () => window.clearTimeout(timer);
  }, [userId, loadedUserId, ready, serialized, conflict, delay, persist]);

  const dirty = Boolean(
    userId && ready && loadedUserId === userId && serialized !== saved,
  );
  useEffect(() => {
    if (!dirty) return;
    const prevent = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", prevent);
    return () => window.removeEventListener("beforeunload", prevent);
  }, [dirty]);

  const useServer = () => {
    if (!conflict || !userId) return;
    revision.current = conflict.revision;
    setRevisionValue(conflict.revision);
    const payload = conflict.payload ?? EMPTY_PREPARATION;
    acknowledged.current = serializePreparation(payload);
    setSaved(acknowledged.current);
    restore.current(payload);
    clearPreparationBackup(userId);
    setConflict(null);
    setError("");
  };
  const keepLocal = () => {
    if (!conflict) return;
    revision.current = conflict.revision;
    setRevisionValue(conflict.revision);
    acknowledged.current = serializePreparation(
      conflict.payload ?? EMPTY_PREPARATION,
    );
    setSaved(acknowledged.current);
    setConflict(null);
    setError("");
  };
  return {
    ready: !userId || (ready && loadedUserId === userId),
    dirty,
    saving,
    error,
    conflict,
    storageError,
    recovered,
    revision: userId ? revisionValue : undefined,
    flush: () => (conflict ? Promise.resolve() : persist()),
    retryLoad: () => setAttempt((count) => count + 1),
    checkConflict: async () => {
      const current = scope.current;
      try {
        const remote = await dossierApi.getPreparation();
        if (current?.active && scope.current === current && userId) {
          verifyOwner(remote, userId);
          setConflict(remote);
        }
      } catch {
        if (current?.active)
          setError(
            "Chưa kiểm tra được bản trên tài khoản. Nội dung đang nhập vẫn được giữ.",
          );
      }
    },
    useServer,
    keepLocal,
    finish: () => {
      if (scope.current && scope.current.owner === userId)
        scope.current.completed = true;
      if (userId) clearPreparationBackup(userId);
    },
  };
}
