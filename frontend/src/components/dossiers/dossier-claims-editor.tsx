"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, dossierApi } from "@/lib/api/client";
import type { DossierClaim, DossierEvidence } from "@/lib/api/types";

const EMPTY: DossierClaim[] = [];

export function DossierClaimsEditor({
  dossierId,
  initialClaims = EMPTY,
  initialRevision = 0,
  criteria,
  evidences,
  readOnly,
  onSaved,
  onUnsavedChange,
}: {
  dossierId: string;
  initialClaims?: DossierClaim[];
  initialRevision?: number;
  criteria: Array<{ key: string; label: string }>;
  evidences: DossierEvidence[];
  readOnly: boolean;
  onSaved: () => void;
  onUnsavedChange: (dirty: boolean) => void;
}) {
  const [claims, setClaims] = useState(initialClaims);
  const [revision, setRevision] = useState(initialRevision);
  const [baseline, setBaseline] = useState(JSON.stringify(initialClaims));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const dirty = !readOnly && JSON.stringify(claims) !== baseline;
  useEffect(
    () => onUnsavedChange(dirty || saving),
    [dirty, onUnsavedChange, saving],
  );
  useEffect(() => {
    if (!dirty) return;
    const prevent = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", prevent);
    const preventNavigation = (event: MouseEvent) => {
      const target =
        event.target instanceof Element
          ? event.target.closest("a[href]")
          : null;
      if (!target || target.getAttribute("href")?.startsWith("#")) return;
      event.preventDefault();
      event.stopPropagation();
      setError("Lưu nhận định hoặc hủy thay đổi trước khi chuyển trang.");
    };
    document.addEventListener("click", preventNavigation, true);
    return () => {
      window.removeEventListener("beforeunload", prevent);
      document.removeEventListener("click", preventNavigation, true);
    };
  }, [dirty]);
  const update = (id: string, patch: Partial<DossierClaim>) =>
    setClaims((current) =>
      current.map((claim) =>
        claim.id === id ? { ...claim, ...patch } : claim,
      ),
    );
  async function save() {
    setSaving(true);
    setError("");
    try {
      const result = await dossierApi.saveClaims(dossierId, revision, claims);
      const acknowledged = result.claims ?? [];
      setClaims(acknowledged);
      setBaseline(JSON.stringify(acknowledged));
      setRevision(result.claimsRevision ?? revision + 1);
      onSaved();
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 409
          ? "Nhận định đã được thay đổi ở phiên khác. Giữ lại nội dung đang nhập và tải lại hồ sơ để đối chiếu trước khi lưu."
          : "Chưa lưu được nhận định. Nội dung đang nhập vẫn được giữ; kiểm tra tiêu chí và tài liệu rồi thử lại.",
      );
    } finally {
      setSaving(false);
    }
  }
  if (!criteria.length && !claims.length) return null;
  return (
    <section
      aria-labelledby="dossier-claims-heading"
      className="space-y-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
    >
      <div>
        <h2 className="text-xl font-bold" id="dossier-claims-heading">
          Nhận định và căn cứ
        </h2>
        <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
          Trình bày thông tin cần chứng minh theo tiêu chí và chọn tài liệu hỗ
          trợ. Đây là nội dung tự khai, chưa phải kết luận kiểm chứng.
        </p>
      </div>
      <fieldset className="space-y-4" disabled={readOnly || saving}>
        <legend className="sr-only">Các nhận định của người nộp</legend>
        {claims.map((claim, index) => (
          <div
            className="space-y-3 border-t border-[var(--theme-border)] pt-4"
            key={claim.id}
          >
            <label className="block text-sm font-semibold">
              Tiêu chí cho nhận định {index + 1}
              <select
                aria-label={`Tiêu chí nhận định ${index + 1}`}
                className="mt-1 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3"
                value={claim.criterionKey}
                onChange={(event) =>
                  update(claim.id, { criterionKey: event.target.value })
                }
              >
                <option value="">Chọn tiêu chí</option>
                {criteria.map(({ key, label }) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-semibold">
              Nội dung nhận định {index + 1}
              <textarea
                className="mt-1 min-h-28 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 font-normal"
                maxLength={2000}
                value={claim.statement}
                onChange={(event) =>
                  update(claim.id, { statement: event.target.value })
                }
              />
            </label>
            <fieldset className="space-y-2">
              <legend className="mb-2 text-sm font-semibold">
                Tài liệu hỗ trợ nhận định {index + 1}
              </legend>
              {evidences.map((evidence) => (
                <label
                  className="flex min-h-11 items-center gap-2 text-sm"
                  key={evidence.id}
                >
                  <input
                    type="checkbox"
                    checked={claim.evidenceMediaIds.includes(
                      evidence.mediaAssetId,
                    )}
                    onChange={(event) =>
                      update(claim.id, {
                        evidenceMediaIds: event.target.checked
                          ? [...claim.evidenceMediaIds, evidence.mediaAssetId]
                          : claim.evidenceMediaIds.filter(
                              (id) => id !== evidence.mediaAssetId,
                            ),
                      })
                    }
                  />
                  {evidence.title}
                </label>
              ))}
              {!evidences.length ? (
                <p className="text-sm text-[var(--theme-muted)]">
                  Thêm tài liệu vào hồ sơ để liên kết minh chứng.
                </p>
              ) : null}
              {claim.evidenceMediaIds.some(
                (id) =>
                  !evidences.some((evidence) => evidence.mediaAssetId === id),
              ) ? (
                <p role="alert" className="text-sm text-red-700">
                  Một tài liệu đã bị gỡ. Chọn lại căn cứ cho nhận định này.
                  {!readOnly ? (
                    <button
                      type="button"
                      className="ml-2 underline"
                      onClick={() =>
                        update(claim.id, {
                          evidenceMediaIds: claim.evidenceMediaIds.filter(
                            (id) =>
                              evidences.some(
                                (evidence) => evidence.mediaAssetId === id,
                              ),
                          ),
                        })
                      }
                    >
                      Gỡ liên kết không còn trong hồ sơ
                    </button>
                  ) : null}
                </p>
              ) : null}
            </fieldset>
            {!readOnly ? (
              <Button
                type="button"
                variant="ghost"
                onClick={() =>
                  setClaims((current) =>
                    current.filter(({ id }) => id !== claim.id),
                  )
                }
              >
                Xóa nhận định {index + 1}
              </Button>
            ) : null}
          </div>
        ))}
        {!readOnly ? (
          <Button
            type="button"
            variant="outline"
            disabled={claims.length >= 50}
            onClick={() =>
              setClaims((current) => [
                ...current,
                {
                  id: crypto.randomUUID(),
                  criterionKey: criteria[0]?.key ?? "",
                  statement: "",
                  evidenceMediaIds: [],
                },
              ])
            }
          >
            Thêm nhận định
          </Button>
        ) : null}
      </fieldset>
      {!readOnly ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            disabled={
              !dirty ||
              saving ||
              claims.some((claim) => !claim.statement.trim())
            }
            onClick={() => void save()}
          >
            {saving ? "Đang lưu nhận định…" : "Lưu nhận định"}
          </Button>
          {dirty ? (
            <Button
              variant="ghost"
              type="button"
              disabled={saving}
              onClick={() => {
                setClaims(JSON.parse(baseline) as DossierClaim[]);
                setError("");
              }}
            >
              Hủy thay đổi nhận định
            </Button>
          ) : null}
          <span className="text-sm text-[var(--theme-muted)]" role="status">
            {dirty ? "Có nội dung chưa lưu" : "Nhận định đã lưu"}
          </span>
        </div>
      ) : null}
      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
